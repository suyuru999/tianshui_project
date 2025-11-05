import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
import matplotlib
import matplotlib.font_manager as fm

# 设置matplotlib后端和中文字体支持
matplotlib.use('Agg')  # 使用非交互式后端
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
import os
import tempfile
from PIL import Image
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class EcologicalIndexCalculator:
    """生态指数计算器"""
    
    def __init__(self, image_path):
        """
        初始化计算器
        
        Args:
            image_path: 遥感影像文件路径
        """
        self.image_path = image_path
        self.dataset = None
        self.bands = None
        self.metadata = None
        
    def load_image(self):
        """加载遥感影像"""
        try:
            logger.info(f"开始加载影像: {self.image_path}")
            logger.info(f"文件是否存在: {os.path.exists(self.image_path)}")
            
            if not os.path.exists(self.image_path):
                logger.error(f"影像文件不存在: {self.image_path}")
                return False
            
            # 尝试使用rasterio打开
            try:
                self.dataset = rasterio.open(self.image_path)
                logger.info(f"rasterio成功打开文件")
                
                # rasterio成功，正常读取
                self.bands = self.dataset.read()
                self.metadata = self.dataset.meta
                
                # 安全检查数组形状
                if self.bands is not None and hasattr(self.bands, 'shape') and len(self.bands.shape) >= 3:
                    logger.info(f"rasterio读取成功，波段数: {self.bands.shape[0]}, 形状: {self.bands.shape}")
                else:
                    logger.error(f"rasterio读取的数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                    return False
                
            except Exception as rasterio_error:
                logger.error(f"rasterio打开失败: {rasterio_error}")
                
                # 尝试使用PIL作为备选方案
                try:
                    logger.info("尝试使用PIL加载影像")
                    pil_image = Image.open(self.image_path)
                    
                    # 转换为numpy数组
                    pil_array = np.array(pil_image)
                    logger.info(f"PIL图像原始形状: {pil_array.shape}")
                    
                    if len(pil_array.shape) == 3:
                        # RGB图像，调整维度顺序为(rasterio格式)
                        self.bands = np.transpose(pil_array, (2, 0, 1))
                        self.metadata = {
                            'driver': 'PNG',
                            'height': pil_array.shape[0],
                            'width': pil_array.shape[1],
                            'count': pil_array.shape[2],
                            'dtype': str(pil_array.dtype),
                            'crs': None,
                            'transform': None
                        }
                        logger.info(f"PIL加载成功，转置后波段数: {self.bands.shape[0]}, 形状: {self.bands.shape}")
                    else:
                        logger.error(f"PIL图像不是3D数组，形状: {pil_array.shape}")
                        return False
                        
                except Exception as pil_error:
                    logger.error(f"PIL加载也失败: {pil_error}")
                    import traceback
                    traceback.print_exc()
                    return False
            
            # 检查波段数
            if hasattr(self, 'bands') and self.bands is not None:
                # 安全检查数组形状
                if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                    logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                    return False
                
                band_count = self.bands.shape[0]
                logger.info(f"成功加载影像: {self.image_path}, 波段数: {band_count}")
                logger.info(f"影像形状: {self.bands.shape}")
                
                if band_count < 3:
                    logger.warning(f"影像波段数不足: {band_count}，至少需要3个波段")
                    return False
                    
                return True
            else:
                logger.error("bands属性未正确设置")
                return False
                
        except Exception as e:
            logger.error(f"加载影像失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_band_availability(self, required_bands):
        """检查是否有足够的波段进行计算"""
        if self.bands is None:
            return False
        
        available_bands = self.bands.shape[0]
        if available_bands < required_bands:
            logger.warning(f"需要{required_bands}个波段，但只有{available_bands}个波段")
            return False
        
        return True
    
    def calculate_ndvi(self):
        """计算NDVI（归一化植被指数）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            logger.info(f"可用波段数: {available_bands}")
            logger.info(f"波段数组形状: {self.bands.shape}")
            logger.info(f"波段数组类型: {type(self.bands)}")
            
            if available_bands < 3:
                logger.error(f"波段数不足，需要至少3个波段，当前只有{available_bands}个")
                return None
            
            # 对于Sentinel-2数据，使用B8A（近红外）和B4（红波段）
            if available_bands >= 8:
                # Sentinel-2: B8A (近红外), B4 (红波段)
                logger.info(f"进入 >= 8 分支，available_bands = {available_bands}")
                nir_band = self.bands[7]  # B8A
                red_band = self.bands[3]   # B4
                logger.info("使用Sentinel-2波段: B8A (近红外), B4 (红波段)")
            elif available_bands >= 5:
                # Landsat-8: B5 (近红外), B4 (红波段)
                logger.info(f"进入 >= 5 分支，available_bands = {available_bands}")
                nir_band = self.bands[4]  # B5
                red_band = self.bands[3]   # B4
                logger.info("使用Landsat-8波段: B5 (近红外), B4 (红波段)")
            elif available_bands == 4:
                # 4波段数据，使用B4 (近红外) 和 B3 (红波段)
                logger.info(f"进入 == 4 分支，available_bands = {available_bands}")
                nir_band = self.bands[3]  # B4 (近红外)
                red_band = self.bands[2]   # B3 (红波段)
                logger.info("使用4波段数据: B4 (近红外), B3 (红波段)")
            elif available_bands == 3:
                # RGB图像，使用G (绿波段) 和 R (红波段) 作为近似
                logger.info(f"进入 == 3 分支，available_bands = {available_bands}")
                nir_band = self.bands[1]  # G
                red_band = self.bands[0]   # R
                logger.info("使用RGB波段: G (绿波段), R (红波段) 作为近似")
            else:
                logger.error(f"不支持的波段配置: {available_bands}")
                return None
            
            # 转换为浮点数进行计算
            nir = nir_band.astype(np.float32)
            red = red_band.astype(np.float32)
            
            # 避免除零错误
            denominator = nir + red
            valid_mask = denominator != 0
            
            # 初始化NDVI数组
            ndvi = np.full_like(nir, np.nan, dtype=np.float32)
            
            # 只对有效像素计算NDVI
            ndvi[valid_mask] = (nir[valid_mask] - red[valid_mask]) / denominator[valid_mask]
            
            # 限制NDVI值范围在[-1, 1]之间
            ndvi = np.clip(ndvi, -1.0, 1.0)
            
            logger.info(f"NDVI计算完成，形状: {ndvi.shape}")
            logger.info(f"NDVI值范围: [{np.nanmin(ndvi):.4f}, {np.nanmax(ndvi):.4f}]")
            
            return ndvi
            
        except Exception as e:
            logger.error(f"计算NDVI失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_ndwi(self):
        """计算NDWI（归一化水体指数）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            logger.info(f"可用波段数: {available_bands}")
            logger.info(f"波段数组形状: {self.bands.shape}")
            logger.info(f"波段数组类型: {type(self.bands)}")
            
            if available_bands < 3:
                logger.error(f"波段数不足，需要至少3个波段，当前只有{available_bands}个")
                return None
            
            # 对于Sentinel-2数据，使用B3（绿波段）和B8A（近红外）
            if available_bands >= 8:
                # Sentinel-2: B3 (绿波段), B8A (近红外)
                logger.info(f"进入 >= 8 分支，available_bands = {available_bands}")
                green_band = self.bands[2]  # B3
                nir_band = self.bands[7]    # B8A
                logger.info("使用Sentinel-2波段: B3 (绿波段), B8A (近红外)")
            elif available_bands >= 5:
                # Landsat-2: B3 (绿波段), B5 (近红外)
                logger.info(f"进入 >= 5 分支，available_bands = {available_bands}")
                green_band = self.bands[2]  # B3
                nir_band = self.bands[4]    # B5
                logger.info("使用Landsat-8波段: B3 (绿波段), B5 (近红外)")
            elif available_bands == 4:
                # 4波段数据，使用B2 (绿波段) 和 B4 (近红外) 或 B3 (红波段)
                logger.info(f"进入 == 4 分支，available_bands = {available_bands}")
                green_band = self.bands[1]  # B2 (绿波段)
                nir_band = self.bands[3]    # B4 (近红外) 或使用B3作为替代
                logger.info("使用4波段数据: B2 (绿波段), B4 (近红外)")
            elif available_bands == 3:
                # RGB图像，使用G (绿波段) 和 R (红波段) 作为近似
                logger.info(f"进入 == 3 分支，available_bands = {available_bands}")
                green_band = self.bands[1]  # G
                nir_band = self.bands[0]    # R
                logger.info("使用RGB波段: G (绿波段), R (红波段) 作为近似")
            else:
                logger.error(f"不支持的波段配置: {available_bands}")
                return None
            
            # 转换为浮点数进行计算
            green = green_band.astype(np.float32)
            nir = nir_band.astype(np.float32)
            
            # 避免除零错误
            denominator = green + nir
            valid_mask = denominator != 0
            
            # 初始化NDWI数组
            ndwi = np.full_like(green, np.nan, dtype=np.float32)
            
            # 只对有效像素计算NDWI
            ndwi[valid_mask] = (green[valid_mask] - nir[valid_mask]) / denominator[valid_mask]
            
            # 限制NDWI值范围在[-1, 1]之间
            ndwi = np.clip(ndwi, -1.0, 1.0)
            
            logger.info(f"NDWI计算完成，形状: {ndwi.shape}")
            logger.info(f"NDWI值范围: [{np.nanmin(ndwi):.4f}, {np.nanmax(ndwi):.4f}]")
            
            return ndwi
            
        except Exception as e:
            logger.error(f"计算NDWI失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_ndbi(self):
        """计算NDBI（归一化建筑指数）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            logger.info(f"可用波段数: {available_bands}")
            
            if available_bands < 3:
                logger.error(f"波段数不足，需要至少3个波段，当前只有{available_bands}个")
                return None
            
            # 对于Sentinel-2数据，使用B11（短波红外）和B8A（近红外）
            if available_bands >= 11:
                # Sentinel-2: B11 (短波红外), B8A (近红外)
                swir_band = self.bands[10]  # B11
                nir_band = self.bands[7]    # B8A
                logger.info("使用Sentinel-2波段: B11 (短波红外), B8A (近红外)")
            elif available_bands >= 6:
                # Landsat-8: B6 (短波红外), B5 (近红外)
                swir_band = self.bands[5]   # B6
                nir_band = self.bands[4]    # B5
                logger.info("使用Landsat-8波段: B6 (短波红外), B5 (近红外)")
            elif available_bands == 3:
                # RGB图像，使用B (蓝波段) 和 R (红波段) 作为近似
                swir_band = self.bands[2]   # B
                nir_band = self.bands[0]    # R
                logger.info("使用RGB波段: B (蓝波段), R (红波段) 作为近似")
            else:
                logger.error(f"不支持的波段配置: {available_bands}")
                return None
            
            # 转换为浮点数进行计算
            swir = swir_band.astype(np.float32)
            nir = nir_band.astype(np.float32)
            
            # 避免除零错误
            denominator = swir + nir
            valid_mask = denominator != 0
            
            # 初始化NDBI数组
            ndbi = np.full_like(swir, np.nan, dtype=np.float32)
            
            # 只对有效像素计算NDBI
            ndbi[valid_mask] = (swir[valid_mask] - nir[valid_mask]) / denominator[valid_mask]
            
            # 限制NDBI值范围在[-1, 1]之间
            ndbi = np.clip(ndbi, -1.0, 1.0)
            
            logger.info(f"NDBI计算完成，形状: {ndbi.shape}")
            logger.info(f"NDBI值范围: [{np.nanmin(ndbi):.4f}, {np.nanmax(ndbi):.4f}]")
            
            return ndbi
            
        except Exception as e:
            logger.error(f"计算NDBI失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_ndsi(self):
        """计算NDSI（归一化积雪指数）"""
        try:
            # 检查波段数
            if not self._check_band_availability(3):
                logger.warning("波段数不足，无法计算NDSI")
                return None
            
            # 对于RGB影像，使用绿波段和蓝波段作为替代
            if self.bands.shape[0] == 3:
                # RGB影像：使用绿波段(1)和蓝波段(0)
                green_band = self.bands[1].astype(float)  # 绿波段
                blue_band = self.bands[0].astype(float)  # 蓝波段
                
                # 简化的NDSI计算（基于绿蓝比值）
                denominator = green_band + blue_band
                denominator[denominator == 0] = 1e-10
                
                ndsi = (green_band - blue_band) / denominator
                logger.info("使用RGB影像计算简化NDSI")
            else:
                # 多光谱影像：根据可用波段数选择合适的波段
                available_bands = self.bands.shape[0]
                if available_bands >= 5:
                    # 使用绿波段(1)和中红外波段(4)
                    green_band = self.bands[1].astype(float)  # 绿波段
                    swir_band = self.bands[4].astype(float)  # 中红外波段
                    logger.info("使用标准NDSI计算: 绿波段(1)和中红外波段(4)")
                elif available_bands == 4:
                    # 4波段数据：使用绿波段(1)和红波段(2)作为替代
                    green_band = self.bands[1].astype(float)  # 绿波段
                    swir_band = self.bands[2].astype(float)  # 红波段作为替代
                    logger.info("使用4波段数据计算简化NDSI: 绿波段(1)和红波段(2)")
                else:
                    logger.warning(f"波段数不足，无法计算NDSI，当前波段数: {available_bands}")
                    return None
                
                denominator = green_band + swir_band
                denominator[denominator == 0] = 1e-10
                
                ndsi = (green_band - swir_band) / denominator
                logger.info("使用多光谱影像计算标准NDSI")
            
            ndsi = np.clip(ndsi, -1, 1)
            return ndsi
        except Exception as e:
            logger.error(f"计算NDSI失败: {e}")
            return None
    
    def calculate_wetness(self):
        """计算湿度指数（基于Tasseled Cap变换）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            if available_bands < 6:
                logger.warning(f"需要至少6个波段来计算湿度指数，当前只有{available_bands}个")
                return None
            
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': 0.1509,
                'green': 0.1973,
                'red': 0.3279,
                'nir': 0.3406,
                'swir1': -0.7112,
                'swir2': -0.4572
            }
            
            # 安全检查数组索引
            if available_bands >= 6:
                wetness = (
                    coefficients['blue'] * self.bands[0] +
                    coefficients['green'] * self.bands[1] +
                    coefficients['red'] * self.bands[2] +
                    coefficients['nir'] * self.bands[3] +
                    coefficients['swir1'] * self.bands[4] +
                    coefficients['swir2'] * self.bands[5]
                )
            else:
                logger.error(f"波段数不足，无法计算湿度指数")
                return None
            
            logger.info(f"湿度指数计算完成，形状: {wetness.shape}")
            return wetness
            
        except Exception as e:
            logger.error(f"计算湿度指数失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_dryness(self):
        """计算干度指数（基于Tasseled Cap变换）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands'    ) or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            if available_bands < 6:
                logger.warning(f"需要至少6个波段来计算干度指数，当前只有{available_bands}个")
                return None
            
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': -0.2936,
                'green': -0.2434,
                'red': -0.5424,
                'nir': 0.7276,
                'swir1': 0.0713,
                'swir2': -0.1608
            }
            
            # 安全检查数组索引
            if available_bands >= 6:
                dryness = (
                    coefficients['blue'] * self.bands[0] +
                    coefficients['green'] * self.bands[1] +
                    coefficients['red'] * self.bands[2] +
                    coefficients['nir'] * self.bands[3] +
                    coefficients['swir1'] * self.bands[4] +
                    coefficients['swir2'] * self.bands[5]
                )
            else:
                logger.error(f"波段数不足，无法计算干度指数")
                return None
            
            logger.info(f"干度指数计算完成，形状: {dryness.shape}")
            return dryness
            
        except Exception as e:
            logger.error(f"计算干度指数失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_heat(self):
        """计算热度指数（基于Tasseled Cap变换）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            if available_bands < 6:
                logger.warning(f"需要至少6个波段来计算热度指数，当前只有{available_bands}个")
                return None
            
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': 0.0315,
                'green': 0.2021,
                'red': 0.3102,
                'nir': 0.1594,
                'swir1': -0.6806,
                'swir2': -0.6109
            }
            
            # 安全检查数组索引
            if available_bands >= 6:
                heat = (
                    coefficients['blue'] * self.bands[0] +
                    coefficients['green'] * self.bands[1] +
                    coefficients['red'] * self.bands[2] +
                    coefficients['nir'] * self.bands[3] +
                    coefficients['swir1'] * self.bands[4] +
                    coefficients['swir2'] * self.bands[5]
                )
            else:
                logger.error(f"波段数不足，无法计算热度指数")
                return None
            
            logger.info(f"热度指数计算完成，形状: {heat.shape}")
            return heat
            
        except Exception as e:
            logger.error(f"计算热度指数失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_greenness(self):
        """计算绿度指数（基于Tasseled Cap变换）"""
        try:
            # 检查是否有足够的波段
            if not hasattr(self, 'bands') or self.bands is None:
                logger.error("没有加载影像数据")
                return None
            
            # 安全检查数组形状
            if not hasattr(self.bands, 'shape') or len(self.bands.shape) < 3:
                logger.error(f"影像数据形状异常: {self.bands.shape if self.bands is not None else 'None'}")
                return None
            
            available_bands = self.bands.shape[0]
            if available_bands < 6:
                logger.warning(f"需要至少6个波段来计算绿度指数，当前只有{available_bands}个")
                return None
            
            # Tasseled Cap变换系数（Landsat 8）
            coefficients = {
                'blue': -0.2941,
                'green': -0.2430,
                'red': -0.5424,
                'nir': 0.7276,
                'swir1': 0.0713,
                'swir2': -0.1608
            }
            
            # 安全检查数组索引
            if available_bands >= 6:
                greenness = (
                    coefficients['blue'] * self.bands[0] +
                    coefficients['green'] * self.bands[1] +
                    coefficients['red'] * self.bands[2] +
                    coefficients['nir'] * self.bands[3] +
                    coefficients['swir1'] * self.bands[4] +
                    coefficients['swir2'] * self.bands[5]
                )
            else:
                logger.error(f"波段数不足，无法计算绿度指数")
                return None
            
            logger.info(f"绿度指数计算完成，形状: {greenness.shape}")
            return greenness
            
        except Exception as e:
            logger.error(f"计算绿度指数失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_rsei(self):
        """计算RSEI（遥感生态指数）"""
        try:
            logger.info("开始计算RSEI...")
            
            # 计算各分量指数
            greenness = self.calculate_greenness()
            wetness = self.calculate_wetness()
            dryness = self.calculate_dryness()
            heat = self.calculate_heat()
            
            if greenness is None or wetness is None or dryness is None or heat is None:
                logger.warning("无法计算RSEI，某些分量指数计算失败")
                return None
            
            logger.info("所有分量指数计算成功，开始RSEI计算")
            
            # 检查数据形状是否一致
            if not all(hasattr(idx, 'shape') for idx in [greenness, wetness, dryness, heat]):
                logger.error("某些分量指数没有shape属性")
                return None
            
            shapes = [greenness.shape, wetness.shape, dryness.shape, heat.shape]
            if len(set(shapes)) > 1:
                logger.error(f"分量指数形状不一致: {shapes}")
                return None
            
            # 检查数组是否为空或无效
            if any(idx.size == 0 for idx in [greenness, wetness, dryness, heat]):
                logger.error("某些分量指数数组为空")
                return None
            
            # 标准化处理
            try:
                scaler = StandardScaler()
                
                # 安全地展平数组
                try:
                    indices = np.stack([greenness.flatten(), wetness.flatten(), 
                                      dryness.flatten(), heat.flatten()], axis=1)
                    logger.info(f"指数数据堆叠完成，形状: {indices.shape}")
                except Exception as stack_error:
                    logger.error(f"数组堆叠失败: {stack_error}")
                    return None
                
                # 去除无效值
                valid_mask = ~np.isnan(indices).any(axis=1)
                indices_valid = indices[valid_mask]
                
                if len(indices_valid) == 0:
                    logger.warning("没有有效的指数数据来计算RSEI")
                    return None
                
                logger.info(f"有效数据点数量: {len(indices_valid)}")
                
                # 标准化
                indices_scaled = scaler.fit_transform(indices_valid)
                
                # 主成分分析
                pca = PCA(n_components=4)
                pca_result = pca.fit_transform(indices_scaled)
                
                logger.info("PCA计算完成")
                
                # 第一主成分作为RSEI
                pc1 = pca_result[:, 0]
                
                # 重建完整图像
                rsei = np.full(indices.shape[0], np.nan)
                rsei[valid_mask] = pc1
                
                # 重塑为原始形状
                try:
                    rsei = rsei.reshape(greenness.shape)
                except Exception as reshape_error:
                    logger.error(f"RSEI重塑失败: {reshape_error}")
                    return None
                
                # 归一化到[0, 1]
                rsei_min = np.nanmin(rsei)
                rsei_max = np.nanmax(rsei)
                if rsei_max > rsei_min:
                    rsei = (rsei - rsei_min) / (rsei_max - rsei_min)
                else:
                    logger.warning("RSEI值范围异常，无法归一化")
                    rsei = np.zeros_like(rsei)
                
                logger.info("RSEI计算完成")
                
                return {
                    'rsei': rsei,
                    'greenness': greenness,
                    'wetness': wetness,
                    'dryness': dryness,
                    'heat': heat,
                    'pca_variance': pca.explained_variance_ratio_,
                    'pca_components': pca.components_
                }
                
            except Exception as pca_error:
                logger.error(f"PCA计算失败: {pca_error}")
                import traceback
                traceback.print_exc()
                return None
                
        except Exception as e:
            logger.error(f"计算RSEI失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_statistics(self, index_data):
        """计算指数统计信息"""
        if index_data is None:
            return None
        
        try:
            # 检查数组是否有效
            if not hasattr(index_data, 'shape') or not hasattr(index_data, 'size'):
                logger.error("输入数据不是有效的numpy数组")
                return None
            
            if index_data.size == 0:
                logger.warning("输入数据为空数组")
                return None
            
            # 去除无效值
            try:
                valid_data = index_data[~np.isnan(index_data)]
            except Exception as mask_error:
                logger.error(f"创建有效数据掩码失败: {mask_error}")
                return None
            
            if len(valid_data) == 0:
                logger.warning("没有有效数据来计算统计信息")
                return None
            
            # 计算基本统计量
            try:
                stats = {
                    'min_value': float(np.nanmin(valid_data)),
                    'max_value': float(np.nanmax(valid_data)),
                    'mean_value': float(np.nanmean(valid_data)),
                    'std_value': float(np.nanstd(valid_data)),
                }
            except Exception as calc_error:
                logger.error(f"计算基本统计量失败: {calc_error}")
                return None
            
            # 分类统计（基于标准差）
            mean_val = stats['mean_value']
            std_val = stats['std_value']
            
            # 定义分类阈值
            thresholds = {
                'excellent': mean_val + 1.5 * std_val,
                'good': mean_val + 0.5 * std_val,
                'moderate': mean_val - 0.5 * std_val,
                'poor': mean_val - 1.5 * std_val,
            }
            
            # 计算各等级像素数量
            pixel_size = 30  # 假设30米分辨率
            area_per_pixel = pixel_size * pixel_size / 1000000  # km²
            
            try:
                excellent_pixels = np.sum(valid_data >= thresholds['excellent'])
                good_pixels = np.sum((valid_data >= thresholds['good']) & (valid_data < thresholds['excellent']))
                moderate_pixels = np.sum((valid_data >= thresholds['moderate']) & (valid_data < thresholds['good']))
                poor_pixels = np.sum((valid_data >= thresholds['poor']) & (valid_data < thresholds['moderate']))
                bad_pixels = np.sum(valid_data < thresholds['poor'])
            except Exception as count_error:
                logger.error(f"计算像素数量失败: {count_error}")
                return None
            
            stats.update({
                'excellent_area': float(excellent_pixels * area_per_pixel),
                'good_area': float(good_pixels * area_per_pixel),
                'moderate_area': float(moderate_pixels * area_per_pixel),
                'poor_area': float(poor_pixels * area_per_pixel),
                'bad_area': float(bad_pixels * area_per_pixel),
            })
            
            logger.info(f"统计信息计算完成，有效数据点: {len(valid_data)}")
            return stats
            
        except Exception as e:
            logger.error(f"计算统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_visualization(self, index_data, index_name, output_path):
        """创建可视化图片"""
        try:
            if index_data is None:
                logger.warning("没有数据来创建可视化")
                return False
            
            # 检查数据是否包含有效值
            if np.all(np.isnan(index_data)):
                logger.warning("所有数据都是NaN，无法创建可视化")
                return False
            
            # 检查数据形状
            if not hasattr(index_data, 'shape'):
                logger.warning("数据没有shape属性")
                return False
            
            if len(index_data.shape) != 2:
                logger.warning(f"数据形状不正确，期望2D数组，实际为{index_data.shape}")
                return False
            
            # 检查数据是否为空
            if index_data.size == 0:
                logger.warning("数据数组为空")
                return False
            
            # matplotlib后端已在文件开头设置
            
            # 创建自定义颜色映射
            colors_list = ['#8B0000', '#FF0000', '#FFA500', '#FFFF00', '#00FF00', '#006400']
            n_bins = 256
            cmap = LinearSegmentedColormap.from_list('custom', colors_list, N=n_bins)
            
            # 创建图形 - 添加错误检查
            try:
                fig, ax = plt.subplots(figsize=(12, 8))
                if fig is None or ax is None:
                    logger.error("matplotlib创建图形失败")
                    return False
            except Exception as subplot_error:
                logger.error(f"创建子图失败: {subplot_error}")
                return False
            
            try:
                # 绘制指数图
                im = ax.imshow(index_data, cmap=cmap, aspect='auto')
                
                # 添加颜色条
                cbar = plt.colorbar(im, ax=ax, shrink=0.8)
                cbar.set_label(f'{index_name} 值', fontsize=12)
                
                # 设置标题和标签
                ax.set_title(f'{index_name} 分布图', fontsize=16, fontweight='bold')
                ax.set_xlabel('像素列', fontsize=12)
                ax.set_ylabel('像素行', fontsize=12)
                
                # 去除坐标轴刻度
                ax.set_xticks([])
                ax.set_yticks([])
                
                # 保存图片
                plt.tight_layout()
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close(fig)  # 明确关闭图形
                
                logger.info(f"成功创建可视化图片: {output_path}")
                return True
                
            except Exception as plot_error:
                logger.error(f"绘制图像失败: {plot_error}")
                plt.close(fig)  # 确保关闭图形
                return False
                
        except Exception as e:
            logger.error(f"创建可视化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_result(self, index_data, output_path):
        """保存计算结果为GeoTIFF文件"""
        try:
            if index_data is None:
                logger.warning("没有数据来保存")
                return False
            
            # 检查数据是否包含有效值
            if np.all(np.isnan(index_data)):
                logger.warning("所有数据都是NaN，无法保存")
                return False
            
            # 检查数据形状
            if not hasattr(index_data, 'shape'):
                logger.warning("数据没有shape属性")
                return False
            
            if len(index_data.shape) != 2:
                logger.warning(f"数据形状不正确，期望2D数组，实际为{index_data.shape}")
                return False
            
            # 检查数据是否为空
            if index_data.size == 0:
                logger.warning("数据数组为空")
                return False
            
            # 检查元数据
            if not self.metadata:
                logger.warning("没有元数据，无法保存")
                return False
            
            # 创建输出元数据
            output_meta = self.metadata.copy()
            output_meta.update({
                'count': 1,
                'dtype': 'float32',
                'nodata': np.nan
            })
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            
            # 保存文件
            try:
                # 明确指定使用GeoTIFF格式，支持Float32数据类型
                output_meta['driver'] = 'GTiff'
                
                with rasterio.open(output_path, 'w', **output_meta) as dst:
                    dst.write(index_data.astype('float32'), 1)
                
                logger.info(f"成功保存结果文件: {output_path}")
                return True
                
            except Exception as write_error:
                logger.error(f"写入文件失败: {write_error}")
                return False
                
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """关闭数据集"""
        try:
            if hasattr(self, 'dataset') and self.dataset is not None:
                self.dataset.close()
                logger.info("数据集已关闭")
            
            # 清理其他资源
            if hasattr(self, 'bands'):
                del self.bands
                self.bands = None
            
            if hasattr(self, 'metadata'):
                del self.metadata
                self.metadata = None
                
            logger.info("计算器资源已清理")
            
        except Exception as e:
            logger.error(f"关闭计算器时出错: {e}")
            import traceback
            traceback.print_exc() 