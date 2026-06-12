"""
气候数据分析模块
提供CSV/Excel文件解析、数据统计分析和图表数据生成功能
"""

import pandas as pd
import numpy as np
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from django.core.files.base import ContentFile
from io import StringIO, BytesIO
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from datetime import datetime
import rasterio
try:
    import seaborn as sns
except ImportError:
    sns = None

from .raster_processing import prepare_raster_upload, raster_band_statistics, preview_array, remove_tree

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ClimateDataAnalyzer:
    """气候数据分析器"""
    
    def __init__(self, file_path: str, file_type: str):
        """
        初始化分析器
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 ('csv' 或 'xlsx')
        """
        self.file_path = file_path
        self.file_type = file_type
        self.df = None
        self.analysis_result = {}
        
    def validate_file_path(self) -> Tuple[bool, str]:
        """
        验证文件路径
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not self.file_path:
            return False, "文件路径为空"
        
        if not os.path.exists(self.file_path):
            return False, f"文件不存在: {self.file_path}"
        
        if not os.path.isfile(self.file_path):
            return False, f"路径不是文件: {self.file_path}"
        
        # 检查文件大小
        file_size = os.path.getsize(self.file_path)
        if file_size == 0:
            return False, "文件为空"
        
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return False, f"文件过大: {file_size / (1024*1024):.2f}MB > 50MB"
        
        return True, ""
    
    def validate_dataframe(self) -> Tuple[bool, str]:
        """
        验证DataFrame数据
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if self.df is None:
            return False, "DataFrame未初始化"
        
        if self.df.empty:
            return False, "数据文件为空"
        
        # 检查行数
        if len(self.df) < 2:
            return False, "数据行数不足，至少需要2行数据"
        
        if len(self.df) > 10000:
            return False, f"数据行数过多: {len(self.df)} > 10000"
        
        # 检查必需的列（支持中英文列名）
        required_columns_en = ['Date', 'Temperature', 'Precipitation', 'Humidity', 'WindSpeed']
        required_columns_zh = ['日期', '温度(°C)', '降水量(mm)', '湿度(%)', '风速(m/s)']
        
        # 创建列名映射（映射到小写，与_preprocess_data保持一致）
        column_mapping = {
            'Date': 'date',
            'Temperature': 'temperature', 
            'Precipitation': 'precipitation',
            'Humidity': 'humidity',
            'WindSpeed': 'wind_speed',
            '日期': 'date',
            '温度(°C)': 'temperature',
            '降水量(mm)': 'precipitation', 
            '湿度(%)': 'humidity',
            '风速(m/s)': 'wind_speed'
        }
        
        missing_columns = []
        found_columns = []
        
        # 检查是否有任何可识别的列名
        for col_en in required_columns_en:
            if col_en in self.df.columns:
                found_columns.append(col_en)
            elif column_mapping.get(col_en) in self.df.columns:
                found_columns.append(col_en)
        
        # 检查中文列名
        for col_zh in required_columns_zh:
            if col_zh in self.df.columns:
                found_columns.append(col_zh)
        
        # 检查是否找到了所有必需的列
        if len(found_columns) < len(required_columns_en):
            missing_columns = []
            for col_en in required_columns_en:
                if col_en not in found_columns and column_mapping.get(col_en) not in [col for col in self.df.columns]:
                    missing_columns.append(f"{col_en} 或 {column_mapping.get(col_en, '')}")
            
            if missing_columns:
                return False, f"缺少必需的列: {missing_columns}"
        
        # 重命名列为标准小写列名
        self.df = self.df.rename(columns=column_mapping)
        
        # 检查数据类型
        numeric_columns = ['temperature', 'precipitation', 'humidity', 'wind_speed']
        for col in numeric_columns:
            if col in self.df.columns:
                # 尝试转换为数值类型
                try:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    # 检查是否有太多NaN值
                    nan_count = self.df[col].isna().sum()
                    if nan_count > len(self.df) * 0.5:  # 超过50%的NaN
                        return False, f"列 {col} 中缺失值过多: {nan_count}/{len(self.df)}"
                except Exception as e:
                    return False, f"列 {col} 数据类型转换失败: {str(e)}"
        
        return True, ""

    def load_data(self) -> bool:
        """
        加载数据文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            # 验证文件路径
            is_valid, error_msg = self.validate_file_path()
            if not is_valid:
                logger.error(f"文件路径验证失败: {error_msg}")
                return False
            
            # 加载数据
            if self.file_type.lower() == 'csv':
                # 尝试不同的编码格式
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                for encoding in encodings:
                    try:
                        self.df = pd.read_csv(self.file_path, encoding=encoding)
                        logger.info(f"成功使用 {encoding} 编码加载CSV文件")
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f"使用 {encoding} 编码加载失败: {str(e)}")
                        continue
                else:
                    raise ValueError("无法使用任何编码格式读取CSV文件")
            elif self.file_type.lower() == 'xlsx':
                try:
                    self.df = pd.read_excel(self.file_path)
                    logger.info("成功加载Excel文件")
                except Exception as e:
                    raise ValueError(f"Excel文件读取失败: {str(e)}")
            else:
                raise ValueError(f"不支持的文件类型: {self.file_type}")
            
            # 验证DataFrame
            is_valid, error_msg = self.validate_dataframe()
            if not is_valid:
                logger.error(f"DataFrame验证失败: {error_msg}")
                return False
            
            # 数据预处理
            self._preprocess_data()
            
            logger.info(f"数据加载完成，共 {len(self.df)} 行数据")
            return True
            
        except Exception as e:
            logger.error(f"加载数据文件失败: {str(e)}")
            return False
    
    def _preprocess_data(self):
        """数据预处理"""
        if self.df is None:
            return
        
        # 标准化列名
        column_mapping = {
            '日期': 'date',
            '温度': 'temperature',
            '温度(°C)': 'temperature',
            '降水量': 'precipitation',
            '降水量(mm)': 'precipitation',
            '湿度': 'humidity',
            '湿度(%)': 'humidity',
            '风速': 'wind_speed',
            '风速(m/s)': 'wind_speed'
        }
        
        # 重命名列
        self.df = self.df.rename(columns=column_mapping)
        
        # 确保日期列是datetime类型
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
        
        # 删除包含NaN的行
        self.df = self.df.dropna()
        
        logger.info(f"数据预处理完成，共 {len(self.df)} 行数据")
    
    def calculate_statistics(self) -> Dict:
        """
        计算统计数据
        
        Returns:
            Dict: 统计数据字典
        """
        if self.df is None:
            return {}
        
        stats = {}
        
        # 温度统计
        if 'temperature' in self.df.columns:
            temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
            stats['temperature'] = {
                'avg': round(temp_data.mean(), 2),
                'max': round(temp_data.max(), 2),
                'min': round(temp_data.min(), 2),
                'std': round(temp_data.std(), 2)
            }
        
        # 降水量统计
        if 'precipitation' in self.df.columns:
            prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
            stats['precipitation'] = {
                'avg': round(prec_data.mean(), 2),
                'max': round(prec_data.max(), 2),
                'min': round(prec_data.min(), 2),
                'std': round(prec_data.std(), 2)
            }
        
        # 湿度统计
        if 'humidity' in self.df.columns:
            hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
            stats['humidity'] = {
                'avg': round(hum_data.mean(), 2),
                'max': round(hum_data.max(), 2),
                'min': round(hum_data.min(), 2),
                'std': round(hum_data.std(), 2)
            }
        
        # 风速统计
        if 'wind_speed' in self.df.columns:
            wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
            stats['wind_speed'] = {
                'avg': round(wind_data.mean(), 2),
                'max': round(wind_data.max(), 2),
                'min': round(wind_data.min(), 2),
                'std': round(wind_data.std(), 2)
            }
        
        return stats
    
    def generate_chart_data(self) -> Dict:
        """
        生成图表数据
        
        Returns:
            Dict: 图表数据字典
        """
        if self.df is None:
            return {}
        
        chart_data = {}
        
        # 温度数据
        if 'temperature' in self.df.columns:
            temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
            chart_data['temperature'] = temp_data.tolist()
        
        # 降水量数据
        if 'precipitation' in self.df.columns:
            prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
            chart_data['precipitation'] = prec_data.tolist()
        
        # 湿度数据
        if 'humidity' in self.df.columns:
            hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
            chart_data['humidity'] = hum_data.tolist()
        
        # 风速数据
        if 'wind_speed' in self.df.columns:
            wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
            chart_data['wind_speed'] = wind_data.tolist()
        
        return chart_data
    
    def generate_visualizations(self) -> Dict[str, str]:
        """
        生成可视化图表
        
        Returns:
            Dict[str, str]: 图表文件路径字典
        """
        if self.df is None:
            return {}
        
        charts = {}
        
        try:
            # 设置图表样式
            plt.style.use('seaborn-v0_8')
            fig_size = (10, 6)
            
            # 温度趋势图
            if 'temperature' in self.df.columns:
                temp_data = pd.to_numeric(self.df['temperature'], errors='coerce').dropna()
                if len(temp_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.plot(range(len(temp_data)), temp_data, 'b-', linewidth=2, marker='o', markersize=4)
                    plt.title('温度趋势分析', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('温度 (°C)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    # 保存图表
                    temp_buffer = BytesIO()
                    plt.savefig(temp_buffer, format='png', dpi=300, bbox_inches='tight')
                    temp_buffer.seek(0)
                    charts['temperature'] = temp_buffer
                    plt.close()
            
            # 降水量柱状图
            if 'precipitation' in self.df.columns:
                prec_data = pd.to_numeric(self.df['precipitation'], errors='coerce').dropna()
                if len(prec_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.bar(range(len(prec_data)), prec_data, color='skyblue', alpha=0.7)
                    plt.title('降水量统计', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('降水量 (mm)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    prec_buffer = BytesIO()
                    plt.savefig(prec_buffer, format='png', dpi=300, bbox_inches='tight')
                    prec_buffer.seek(0)
                    charts['precipitation'] = prec_buffer
                    plt.close()
            
            # 湿度面积图
            if 'humidity' in self.df.columns:
                hum_data = pd.to_numeric(self.df['humidity'], errors='coerce').dropna()
                if len(hum_data) > 0:
                    plt.figure(figsize=fig_size)
                    plt.fill_between(range(len(hum_data)), hum_data, alpha=0.6, color='green')
                    plt.plot(range(len(hum_data)), hum_data, 'g-', linewidth=2)
                    plt.title('湿度变化', fontsize=16, fontweight='bold')
                    plt.xlabel('时间序列', fontsize=12)
                    plt.ylabel('湿度 (%)', fontsize=12)
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    
                    hum_buffer = BytesIO()
                    plt.savefig(hum_buffer, format='png', dpi=300, bbox_inches='tight')
                    hum_buffer.seek(0)
                    charts['humidity'] = hum_buffer
                    plt.close()
            
            # 风速雷达图
            if 'wind_speed' in self.df.columns:
                wind_data = pd.to_numeric(self.df['wind_speed'], errors='coerce').dropna()
                if len(wind_data) > 0:
                    plt.figure(figsize=(8, 8))
                    angles = np.linspace(0, 2 * np.pi, len(wind_data), endpoint=False)
                    values = wind_data.tolist()
                    values += values[:1]  # 闭合图形
                    angles = np.concatenate((angles, [angles[0]]))
                    
                    ax = plt.subplot(111, projection='polar')
                    ax.plot(angles, values, 'o-', linewidth=2, color='red')
                    ax.fill(angles, values, alpha=0.25, color='red')
                    ax.set_title('风速分析', fontsize=16, fontweight='bold', pad=20)
                    ax.grid(True)
                    
                    wind_buffer = BytesIO()
                    plt.savefig(wind_buffer, format='png', dpi=300, bbox_inches='tight')
                    wind_buffer.seek(0)
                    charts['wind_speed'] = wind_buffer
                    plt.close()
            
        except Exception as e:
            logger.error(f"生成可视化图表失败: {str(e)}")
        
        return charts
    
    def analyze(self) -> Dict:
        """
        执行完整的数据分析
        
        Returns:
            Dict: 分析结果字典
        """
        if not self.load_data():
            return {'error': '数据加载失败'}
        
        # 计算统计数据
        statistics = self.calculate_statistics()
        
        # 生成图表数据
        chart_data = self.generate_chart_data()
        
        # 生成可视化图表
        charts = self.generate_visualizations()
        
        result = {
            'statistics': statistics,
            'chart_data': chart_data,
            'charts': charts,
            'data_count': len(self.df) if self.df is not None else 0
        }
        
        return result


def analyze_climate_data(file_path: str, file_type: str) -> Dict:
    """
    分析气候数据的便捷函数
    
    Args:
        file_path: 文件路径
        file_type: 文件类型
        
    Returns:
        Dict: 分析结果
    """
    if file_type.lower() in ['tif', 'tiff', 'zip']:
        return analyze_climate_raster(file_path, file_type)

    analyzer = ClimateDataAnalyzer(file_path, file_type)
    return analyzer.analyze()


def _infer_climate_metric(file_path):
    name = os.path.basename(file_path).lower()
    if any(key in name for key in ['降水', 'precip', 'rain']):
        return 'precipitation'
    if any(key in name for key in ['湿度', 'humidity', 'wet']):
        return 'humidity'
    if any(key in name for key in ['风速', 'wind']):
        return 'wind_speed'
    if any(key in name for key in ['温度', '地温', 'lst', 'temp']):
        return 'temperature'
    return 'temperature'


def _sample_raster_values(path, max_points=240):
    data = preview_array(path, max_size=700)
    valid = data[np.isfinite(data)]
    if valid.size == 0:
        return []
    if valid.size > max_points:
        indices = np.linspace(0, valid.size - 1, max_points).astype(int)
        valid = valid[indices]
    return [round(float(value), 4) for value in valid]


def analyze_climate_raster(file_path: str, file_type: str) -> Dict:
    cleanup_dirs = []
    raster_path = file_path
    try:
        if file_type.lower() == 'zip':
            result_dir = os.path.join(os.path.dirname(file_path), f'{Path(file_path).stem}_converted')
            os.makedirs(result_dir, exist_ok=True)
            raster_path, cleanup_dirs = prepare_raster_upload(file_path, result_dir)

        with rasterio.open(raster_path) as dataset:
            band_count = dataset.count
            width = dataset.width
            height = dataset.height
            crs = str(dataset.crs) if dataset.crs else None

        stats = raster_band_statistics(raster_path, include_classes=False)
        metric = _infer_climate_metric(file_path)
        metric_stats = {
            'avg': round(stats['mean_value'], 4),
            'max': round(stats['max_value'], 4),
            'min': round(stats['min_value'], 4),
            'std': round(stats['std_value'], 4),
        }
        statistics = {metric: metric_stats}
        chart_data = {metric: _sample_raster_values(raster_path)}
        chart_data['raster_metadata'] = {
            'filename': os.path.basename(file_path),
            'bands_count': band_count,
            'width': width,
            'height': height,
            'crs': crs,
        }
        return {
            'statistics': statistics,
            'chart_data': chart_data,
            'charts': {},
            'data_count': width * height,
        }
    finally:
        for cleanup_dir in cleanup_dirs:
            remove_tree(cleanup_dir)
