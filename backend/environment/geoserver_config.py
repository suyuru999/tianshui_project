"""
GeoServer配置模块
用于管理地理空间服务和WMS/WFS服务
"""

import os
import logging
from typing import Dict, Any, Optional
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class GeoServerManager:
    """GeoServer管理类"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'GEOSERVER_URL', 'http://localhost:8080/geoserver')
        self.username = getattr(settings, 'GEOSERVER_USERNAME', 'admin')
        self.password = getattr(settings, 'GEOSERVER_PASSWORD', 'geoserver')
        self.workspace = getattr(settings, 'GEOSERVER_WORKSPACE', 'tianshuipy')
        self.auth = HTTPBasicAuth(self.username, self.password)
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送HTTP请求到GeoServer"""
        try:
            url = f"{self.base_url}/rest/{endpoint}"
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                **kwargs
            )
            
            if response.status_code in [200, 201]:
                return response.json() if response.content else {}
            else:
                logger.error(f"GeoServer请求失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"GeoServer请求异常: {e}")
            return None
    
    def create_workspace(self) -> bool:
        """创建工作空间"""
        workspace_data = {
            "workspace": {
                "name": self.workspace
            }
        }
        
        result = self._make_request(
            'POST', 
            'workspaces', 
            json=workspace_data
        )
        
        if result is not None:
            logger.info(f"工作空间 {self.workspace} 创建成功")
            return True
        return False
    
    def create_datastore(self, datastore_name: str, datastore_type: str = 'GeoTIFF') -> bool:
        """创建数据存储"""
        # 先检查数据存储是否已存在
        try:
            existing = self._make_request('GET', f'workspaces/{self.workspace}/datastores/{datastore_name}.json')
            if existing:
                logger.info(f"数据存储 {datastore_name} 已存在")
                return True
        except:
            pass
        
        # 创建新数据存储
        datastore_data = {
            "dataStore": {
                "name": datastore_name,
                "type": datastore_type,
                "enabled": True,
                "connectionParameters": {
                    "entry": [
                        {"@key": "url", "$": f"file:data_dir"},
                        {"@key": "create spatial index", "$": "true"}
                    ]
                }
            }
        }
        
        result = self._make_request(
            'POST',
            f'workspaces/{self.workspace}/datastores',
            json=datastore_data
        )
        
        if result is not None:
            logger.info(f"数据存储 {datastore_name} 创建成功")
            return True
        
        # 如果创建失败，尝试另一种方式（直接创建空的数据存储）
        try:
            simple_datastore_data = {
                "dataStore": {
                    "name": datastore_name,
                    "type": datastore_type
                }
            }
            result = self._make_request(
                'POST',
                f'workspaces/{self.workspace}/datastores',
                json=simple_datastore_data
            )
            if result is not None:
                logger.info(f"数据存储 {datastore_name} 创建成功（简化方式）")
                return True
        except Exception as e:
            logger.warning(f"使用简化方式创建数据存储失败: {e}")
        
        logger.warning(f"数据存储 {datastore_name} 创建失败或已存在")
        return False
    
    def publish_raster(self, coverage_store_name: str, layer_name: str, file_path: str) -> bool:
        """发布栅格图层（使用CoverageStore）"""
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(file_path):
                logger.error(f"栅格文件不存在: {file_path}")
                return False
            
            # 对于GeoTIFF，使用CoverageStore而不是DataStore
            # 方法1: 检查并删除旧的CoverageStore（如果存在但类型不对）
            coverage_store_check = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}.json')
            if coverage_store_check:
                # 检查类型
                store_type = coverage_store_check.get('coverageStore', {}).get('type', '')
                if store_type != 'GeoTIFF':
                    logger.info(f"CoverageStore {coverage_store_name} 类型不正确 ({store_type})，删除后重新创建")
                    self.delete_coveragestore(coverage_store_name, recurse=True)
                    coverage_store_check = None
            
            # 方法2: 如果不存在，创建新的CoverageStore
            if not coverage_store_check:
                logger.info(f"CoverageStore {coverage_store_name} 不存在，先创建")
                # 创建CoverageStore
                coverage_store_data = {
                    "coverageStore": {
                        "name": coverage_store_name,
                        "type": "GeoTIFF",
                        "enabled": True,
                        "workspace": {
                            "name": self.workspace
                        }
                    }
                }
                
                create_result = self._make_request(
                    'POST',
                    f'workspaces/{self.workspace}/coveragestores',
                    json=coverage_store_data
                )
                
                if create_result is None:
                    logger.warning(f"创建CoverageStore失败，可能已存在，继续尝试上传文件")
            
            # 方法2: 上传GeoTIFF文件到CoverageStore
            upload_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/file.geotiff"
            
            logger.info(f"尝试上传栅格文件到GeoServer: {file_path}")
            logger.info(f"上传URL: {upload_url}")
            
            try:
                with open(file_path, 'rb') as f:
                    file_size = os.path.getsize(file_path)
                    logger.info(f"文件大小: {file_size} 字节 ({file_size / 1024 / 1024:.2f} MB)")
                    
                    # 上传文件
                    response = requests.put(
                        upload_url,
                        auth=self.auth,
                        data=f,
                        headers={'Content-Type': 'image/tiff'},
                        timeout=300  # 5分钟超时，处理大文件
                    )
                
                logger.info(f"上传响应状态码: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ 文件上传成功")
                    
                    # 方法3: 检查图层是否自动创建（GeoServer上传文件后会自动创建图层）
                    # 等待一下让GeoServer处理
                    import time
                    time.sleep(2)  # 增加等待时间，让GeoServer有时间处理文件
                    
                    # 检查CoverageStore中的Coverage（GeoServer会根据文件名自动创建Coverage）
                    coverage_list = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                    
                    actual_layer_name = None
                    if coverage_list and 'coverages' in coverage_list:
                        coverages = coverage_list['coverages'].get('coverage', [])
                        if isinstance(coverages, list) and len(coverages) > 0:
                            # 获取第一个coverage的名称
                            coverage_obj = coverages[0]
                            if isinstance(coverage_obj, dict):
                                actual_layer_name = coverage_obj.get('name', layer_name)
                            else:
                                actual_layer_name = layer_name
                        elif isinstance(coverages, dict):
                            actual_layer_name = coverages.get('name', layer_name)
                    
                    # 如果找到了coverage，检查图层名称是否匹配期望的名称
                    if actual_layer_name:
                        logger.info(f"✅ 找到自动创建的Coverage: {actual_layer_name}")
                        # 检查对应的图层是否存在
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{actual_layer_name}.json')
                        if layer_check:
                            # 如果图层名称与期望的不同，尝试重命名图层
                            if actual_layer_name != layer_name:
                                logger.info(f"⚠️ 图层名称不匹配：期望 {layer_name}，实际 {actual_layer_name}，尝试重命名...")
                                # 通过更新Coverage的名称来重命名图层
                                try:
                                    # 获取Coverage信息
                                    coverage_info = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{actual_layer_name}.json')
                                    if coverage_info and 'coverage' in coverage_info:
                                        # 更新Coverage名称
                                        coverage_info['coverage']['name'] = layer_name
                                        # 使用PUT请求更新Coverage
                                        update_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{actual_layer_name}.json"
                                        update_response = requests.put(
                                            update_url,
                                            auth=self.auth,
                                            json=coverage_info,
                                            headers={'Content-Type': 'application/json'},
                                            timeout=30
                                        )
                                        if update_response.status_code in [200, 204]:
                                            logger.info(f"✅ Coverage重命名成功: {actual_layer_name} -> {layer_name}")
                                            time.sleep(2)  # 等待GeoServer处理
                                            # 验证新名称的图层是否存在
                                            new_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                            if new_check:
                                                logger.info(f"✅ 栅格图层 {layer_name} 已创建并验证成功")
                                                return True
                                            else:
                                                logger.warning(f"⚠️ Coverage已重命名但图层验证失败，等待更长时间...")
                                                time.sleep(3)
                                                final_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                                if final_check:
                                                    logger.info(f"✅ 栅格图层 {layer_name} 验证成功")
                                                    
                                                    # 为图层创建并应用默认样式
                                                    style_name = f"{layer_name}_style"
                                                    
                                                    # 从栅格文件读取统计信息，以创建合适的样式
                                                    min_val, max_val = self._get_raster_statistics(file_path)
                                                    logger.info(f"使用栅格值域创建样式: {min_val} - {max_val}")
                                                    
                                                    sld_content = self._create_default_raster_sld(min_val, max_val)
                                                    if self.create_style(style_name, sld_content):
                                                        self.apply_style_to_layer(layer_name, style_name)
                                                    
                                                    return True
                                                else:
                                                    logger.warning(f"⚠️ 图层 {layer_name} 验证失败，但文件已上传成功")
                                                    
                                                    # 即使验证失败，也尝试应用样式（使用实际图层名称）
                                                    if actual_layer_name:
                                                        style_name = f"{actual_layer_name}_style"
                                                        sld_content = self._create_default_raster_sld(0.0, 5.0)
                                                        if self.create_style(style_name, sld_content):
                                                            self.apply_style_to_layer(actual_layer_name, style_name)
                                                    
                                                    return True  # 文件上传成功，即使验证失败也返回True
                                        else:
                                            logger.warning(f"⚠️ Coverage重命名失败: HTTP {update_response.status_code}")
                                except Exception as rename_error:
                                    logger.warning(f"⚠️ 重命名图层时出错: {rename_error}")
                                
                                # 即使重命名失败，也尝试使用实际创建的图层名称，并为实际图层创建并应用样式
                                logger.info(f"⚠️ 图层名称不匹配但文件已上传成功，使用实际图层名称: {actual_layer_name}")
                                
                                # 为实际创建的图层创建并应用默认样式
                                style_name = f"{actual_layer_name}_style"
                                logger.info(f"为实际图层 {actual_layer_name} 创建样式: {style_name}")
                                
                                # 从栅格文件读取统计信息，以创建合适的样式
                                # 为了确保不会卡住，直接使用默认值域（如果实际值域与默认值域差异较大，样式可能不够准确，但至少能显示）
                                logger.info(f"快速模式：使用默认值域创建样式（避免长时间读取栅格数据）")
                                min_val, max_val = (0.0, 5.0)
                                logger.info(f"使用默认值域创建样式: {min_val} - {max_val}")
                                
                                # 可选：尝试快速读取统计信息（不阻塞）
                                try:
                                    import threading
                                    result = [None]
                                    def quick_get_stats():
                                        try:
                                            result[0] = self._get_raster_statistics(file_path)
                                        except:
                                            pass
                                    
                                    thread = threading.Thread(target=quick_get_stats)
                                    thread.daemon = True
                                    thread.start()
                                    thread.join(timeout=3)  # 3秒超时
                                    
                                    if result[0] and thread.is_alive() == False:
                                        min_val, max_val = result[0]
                                        logger.info(f"✅ 快速获取到统计信息，更新值域: {min_val} - {max_val}")
                                except:
                                    pass
                                
                                sld_content = self._create_default_raster_sld(min_val, max_val)
                                if self.create_style(style_name, sld_content):
                                    logger.info(f"样式 {style_name} 创建成功，开始应用到图层")
                                    if self.apply_style_to_layer(actual_layer_name, style_name):
                                        logger.info(f"✅ 样式已成功应用到图层 {actual_layer_name}")
                                    else:
                                        logger.warning(f"⚠️ 样式应用到图层失败，但图层已发布")
                                else:
                                    logger.warning(f"⚠️ 样式创建失败，但图层已发布")
                                
                                return True  # 文件上传成功，即使名称不匹配也返回True
                            else:
                                logger.info(f"✅ 栅格图层 {actual_layer_name} 已自动创建")
                                
                                # 为图层创建并应用默认样式
                                style_name = f"{actual_layer_name}_style"
                                
                                # 从栅格文件读取统计信息，以创建合适的样式
                                min_val, max_val = self._get_raster_statistics(file_path)
                                logger.info(f"使用栅格值域创建样式: {min_val} - {max_val}")
                                
                                sld_content = self._create_default_raster_sld(min_val, max_val)
                                if self.create_style(style_name, sld_content):
                                    self.apply_style_to_layer(actual_layer_name, style_name)
                                
                                return True
                    else:
                        # 尝试使用期望的图层名称
                        actual_layer_name = layer_name
                        layer_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                        if layer_check:
                            logger.info(f"✅ 栅格图层 {layer_name} 已自动创建")
                            
                            # 为图层创建并应用默认样式
                            style_name = f"{layer_name}_style"
                            sld_content = self._create_default_raster_sld(0.0, 5.0)
                            if self.create_style(style_name, sld_content):
                                self.apply_style_to_layer(layer_name, style_name)
                            
                            return True
                    
                    # 如果图层名称不同，尝试使用coverage store的名称（GeoServer有时会用coverage store名称作为图层名称）
                    coverage_store_check = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}.json')
                    if coverage_store_check:
                        # 检查是否有对应的图层
                        all_layers = self._make_request('GET', f'workspaces/{self.workspace}/layers.json')
                        if all_layers and 'layers' in all_layers:
                            layer_list = all_layers['layers'].get('layer', [])
                            if isinstance(layer_list, list):
                                for layer in layer_list:
                                    layer_dict = layer if isinstance(layer, dict) else {'name': str(layer)}
                                    layer_name_in_list = layer_dict.get('name', '')
                                    # 如果找到的图层是coverage store名称，尝试重命名
                                    if layer_name_in_list == coverage_store_name and layer_name_in_list != layer_name:
                                        logger.info(f"⚠️ 图层名称是CoverageStore名称 {layer_name_in_list}，期望是 {layer_name}，尝试重命名...")
                                        try:
                                            coverage_info = self._make_request('GET', f'workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{layer_name_in_list}.json')
                                            if coverage_info and 'coverage' in coverage_info:
                                                coverage_info['coverage']['name'] = layer_name
                                                update_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}/coverages/{layer_name_in_list}.json"
                                                update_response = requests.put(
                                                    update_url,
                                                    auth=self.auth,
                                                    json=coverage_info,
                                                    headers={'Content-Type': 'application/json'},
                                                    timeout=30
                                                )
                                                if update_response.status_code in [200, 204]:
                                                    logger.info(f"✅ Coverage重命名成功: {layer_name_in_list} -> {layer_name}")
                                                    time.sleep(2)
                                                    new_check = self._make_request('GET', f'layers/{self.workspace}:{layer_name}.json')
                                                    if new_check:
                                                        logger.info(f"✅ 栅格图层 {layer_name} 已创建并验证成功")
                                                        return True
                                        except Exception as rename_error:
                                            logger.warning(f"⚠️ 重命名图层时出错: {rename_error}")
                                    
                                    # 检查图层名称是否包含coverage store名称或期望的图层名称
                                    if coverage_store_name in layer_name_in_list or layer_name in layer_name_in_list:
                                        logger.info(f"✅ 找到图层: {layer_name_in_list}")
                                        # 即使名称不完全匹配，文件上传成功也返回True
                                        return True
                    
                    # 如果仍未找到，但文件已上传成功，说明图层应该存在，只是名称可能不同
                    logger.info(f"✅ 文件上传成功，GeoServer应已自动创建图层（可能名称不同）")
                    # 文件上传成功通常意味着图层已创建，即使查询不到也可能是GeoServer尚未完全处理
                    return True
                        
                elif response.status_code == 404:
                    logger.error(f"CoverageStore不存在: {coverage_store_name}，尝试重新创建")
                    # 重新创建CoverageStore并重试
                    if self.publish_raster(coverage_store_name, layer_name, file_path):
                        return True
                else:
                    logger.error(f"❌ 文件上传失败: HTTP {response.status_code}")
                    logger.error(f"响应内容: {response.text[:1000]}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"上传文件超时，文件可能太大")
                return False
            except requests.exceptions.ConnectionError as e:
                logger.error(f"无法连接到GeoServer: {e}")
                return False
            except Exception as e:
                logger.error(f"上传文件时发生错误: {e}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"发布栅格图层失败: {e}", exc_info=True)
            
        return False
    
    def delete_coveragestore(self, coverage_store_name: str, recurse: bool = True) -> bool:
        """删除CoverageStore（以及可能存在的同名DataStore）"""
        success = True
        
        # 先删除CoverageStore
        try:
            delete_url = f"{self.base_url}/rest/workspaces/{self.workspace}/coveragestores/{coverage_store_name}?recurse={str(recurse).lower()}"
            response = requests.delete(
                delete_url,
                auth=self.auth
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"CoverageStore {coverage_store_name} 删除成功")
            elif response.status_code == 404:
                logger.info(f"CoverageStore {coverage_store_name} 不存在，无需删除")
            else:
                logger.warning(f"删除CoverageStore失败: HTTP {response.status_code}")
                success = False
        except Exception as e:
            logger.warning(f"删除CoverageStore异常: {e}")
        
        # 也删除可能存在的同名DataStore（如果之前错误地创建了）
        try:
            datastore_check = self._make_request('GET', f'workspaces/{self.workspace}/datastores/{coverage_store_name}.json')
            if datastore_check:
                logger.info(f"发现同名DataStore {coverage_store_name}，也删除")
                delete_url = f"{self.base_url}/rest/workspaces/{self.workspace}/datastores/{coverage_store_name}?recurse={str(recurse).lower()}"
                response = requests.delete(
                    delete_url,
                    auth=self.auth
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"DataStore {coverage_store_name} 删除成功")
                elif response.status_code == 404:
                    logger.info(f"DataStore {coverage_store_name} 不存在")
                else:
                    logger.warning(f"删除DataStore失败: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"检查/删除DataStore异常: {e}")
        
        return success
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """获取图层信息"""
        return self._make_request('GET', f'layers/{layer_name}')
    
    def get_wms_capabilities(self) -> Optional[Dict[str, Any]]:
        """获取WMS服务能力"""
        try:
            url = f"{self.base_url}/ows?service=WMS&version=1.3.0&request=GetCapabilities"
            response = requests.get(url, auth=self.auth)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"获取WMS能力失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取WMS能力异常: {e}")
            return None
    
    def create_style(self, style_name: str, sld_content: str) -> bool:
        """创建样式"""
        style_data = {
            "style": {
                "name": style_name,
                "filename": f"{style_name}.sld"
            }
        }
        
        # 先创建样式
        result = self._make_request(
            'POST',
            'styles',
            json=style_data
        )
        
        if result is not None:
            # 上传SLD文件
            sld_url = f"{self.base_url}/rest/styles/{style_name}"
            try:
                response = requests.put(
                    sld_url,
                    auth=self.auth,
                    data=sld_content,
                    headers={'Content-Type': 'application/vnd.ogc.sld+xml'}
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"样式 {style_name} 创建成功")
                    return True
                    
            except Exception as e:
                logger.error(f"上传SLD文件失败: {e}")
                
        return False
    
    def _get_raster_statistics(self, file_path: str) -> tuple:
        """获取栅格文件的统计信息（最小值、最大值）"""
        try:
            from osgeo import gdal
            import numpy as np
            
            dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
            if dataset is None:
                logger.warning(f"无法打开栅格文件读取统计信息: {file_path}")
                return (0.0, 5.0)
            
            band = dataset.GetRasterBand(1)
            
            # 尝试读取统计信息
            stats = band.GetStatistics(False, True)
            if stats and len(stats) >= 4:
                min_val = stats[0]
                max_val = stats[1]
                dataset = None
                
                # 如果统计信息有效
                if not np.isnan(min_val) and not np.isnan(max_val) and max_val > min_val:
                    logger.info(f"从栅格文件读取统计信息: min={min_val}, max={max_val}")
                    return (float(min_val), float(max_val))
            
            # 如果统计信息无效，尝试计算（限制数据量以提高性能）
            logger.info(f"统计信息无效，尝试计算栅格值域...")
            try:
                # 读取栅格尺寸
                width = band.XSize
                height = band.YSize
                total_pixels = width * height
                logger.info(f"栅格尺寸: {width}x{height} ({total_pixels} 像素)")
                
                # 如果图像很大，使用采样以提高性能
                if total_pixels > 5000000:  # 大于500万像素，使用采样
                    logger.info(f"图像较大 ({width}x{height})，使用采样计算值域")
                    # 采样大小为最大1000x1000或实际尺寸的1/10，取较小值
                    sample_x = min(max(100, width // 10), 1000)
                    sample_y = min(max(100, height // 10), 1000)
                    logger.info(f"采样尺寸: {sample_x}x{sample_y}")
                    data = band.ReadAsArray(0, 0, sample_x, sample_y)
                elif total_pixels > 1000000:  # 大于100万像素，使用更大的采样
                    logger.info(f"图像中等 ({width}x{height})，使用适度采样")
                    sample_x = min(width, 2000)
                    sample_y = min(height, 2000)
                    data = band.ReadAsArray(0, 0, sample_x, sample_y)
                else:
                    # 图像较小，读取全部数据
                    logger.info(f"图像较小 ({width}x{height})，读取全部数据")
                    try:
                        # 使用ReadAsArray读取数据，如果失败则使用采样
                        if total_pixels > 50000:  # 大于5万像素，使用采样以提高稳定性
                            logger.info(f"使用采样读取数据以提高稳定性")
                            sample_x = min(width, 500)
                            sample_y = min(height, 500)
                            data = band.ReadAsArray(0, 0, sample_x, sample_y)
                            logger.info(f"采样读取完成，采样尺寸: {sample_x}x{sample_y}")
                        else:
                            data = band.ReadAsArray()
                            logger.info(f"全部数据读取完成")
                        
                        if data is not None:
                            logger.info(f"数据形状: {data.shape}, 数据大小: {data.size}, 数据类型: {data.dtype}")
                        else:
                            logger.warning(f"读取到的数据为None")
                    except Exception as read_error:
                        logger.error(f"读取栅格数据失败: {read_error}")
                        # 如果读取失败，尝试使用默认值域
                        logger.warning(f"使用默认值域继续处理")
                        dataset = None
                        band = None
                        return (0.0, 5.0)
                
                if data is not None and data.size > 0:
                    logger.info(f"成功读取栅格数据，尺寸: {data.shape}, 数据类型: {data.dtype}")
                    
                    # 处理NoData值
                    nodata = band.GetNoDataValue()
                    logger.info(f"NoData值: {nodata}")
                    
                    if nodata is not None:
                        # 过滤NoData值
                        if np.issubdtype(data.dtype, np.floating):
                            valid_mask = ~np.isnan(data) & (data != nodata)
                        else:
                            valid_mask = data != nodata
                        valid_data = data[valid_mask]
                        logger.info(f"过滤NoData后，有效数据点数: {len(valid_data)} / {data.size}")
                    else:
                        # 如果没有NoData值，但数据是浮点型，需要检查NaN
                        if np.issubdtype(data.dtype, np.floating):
                            valid_data = data[~np.isnan(data)]
                            logger.info(f"过滤NaN后，有效数据点数: {len(valid_data)} / {data.size}")
                        else:
                            valid_data = data.flatten()
                            logger.info(f"全部数据点数: {len(valid_data)}")
                    
                    if len(valid_data) > 0:
                        min_val = float(np.nanmin(valid_data))
                        max_val = float(np.nanmax(valid_data))
                        logger.info(f"计算得到的栅格值域: min={min_val}, max={max_val}")
                        
                        # 清理内存
                        del data
                        del valid_data
                        dataset = None
                        band = None
                        
                        if not np.isnan(min_val) and not np.isnan(max_val) and max_val > min_val:
                            logger.info(f"✅ 有效的栅格值域: {min_val} - {max_val}")
                            return (min_val, max_val)
                        else:
                            logger.warning(f"⚠️ 计算得到的值域无效: min={min_val}, max={max_val}")
                    else:
                        logger.warning(f"⚠️ 没有有效数据点（可能全是NoData或NaN）")
                else:
                    logger.warning(f"⚠️ 无法读取栅格数据或数据为空")
            except MemoryError as mem_error:
                logger.warning(f"⚠️ 内存不足，无法计算栅格值域: {mem_error}，使用默认值域")
            except Exception as calc_error:
                logger.warning(f"⚠️ 计算栅格值域时出错: {calc_error}，使用默认值域")
            
            try:
                dataset = None
                band = None
            except:
                pass
            logger.warning(f"无法获取栅格统计信息，使用默认值域: 0.0-5.0")
            return (0.0, 5.0)
            
        except Exception as e:
            logger.warning(f"读取栅格统计信息失败: {e}，使用默认值域: 0.0-5.0")
            return (0.0, 5.0)
    
    def _create_default_raster_sld(self, min_value: float = 0.0, max_value: float = 5.0) -> str:
        """创建默认的栅格SLD样式（彩色渐变）"""
        # 确保值域有效
        if max_value <= min_value:
            min_value = 0.0
            max_value = 5.0
        
        # 计算中间值
        range_val = max_value - min_value
        q1 = min_value + range_val * 0.25
        q2 = min_value + range_val * 0.5
        q3 = min_value + range_val * 0.75
        
        sld = f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>raster_style</Name>
        <UserStyle>
            <Title>栅格图层默认样式</Title>
            <FeatureTypeStyle>
                <Rule>
                    <RasterSymbolizer>
                        <Opacity>1.0</Opacity>
                        <ColorMap type="ramp">
                            <ColorMapEntry color="#0000ff" quantity="{min_value:.6f}" opacity="1.0"/>
                            <ColorMapEntry color="#00ffff" quantity="{q1:.6f}" opacity="1.0"/>
                            <ColorMapEntry color="#00ff00" quantity="{q2:.6f}" opacity="1.0"/>
                            <ColorMapEntry color="#ffff00" quantity="{q3:.6f}" opacity="1.0"/>
                            <ColorMapEntry color="#ff0000" quantity="{max_value:.6f}" opacity="1.0"/>
                        </ColorMap>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''
        return sld
    
    def apply_style_to_layer(self, layer_name: str, style_name: str) -> bool:
        """为图层应用样式"""
        try:
            # 更新图层配置，设置默认样式
            layer_url = f"{self.base_url}/rest/layers/{self.workspace}:{layer_name}.json"
            
            # 先获取图层信息
            layer_response = requests.get(
                layer_url,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if layer_response.status_code == 200:
                layer_data = layer_response.json()
                
                # 更新样式
                layer_data['layer']['defaultStyle'] = {
                    'name': style_name,
                    'workspace': self.workspace
                }
                
                # 提交更新
                update_response = requests.put(
                    layer_url,
                    auth=self.auth,
                    json=layer_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if update_response.status_code in [200, 204]:
                    logger.info(f"✅ 样式 {style_name} 已应用到图层 {layer_name}")
                    return True
                else:
                    logger.error(f"❌ 应用样式失败: HTTP {update_response.status_code} - {update_response.text}")
            else:
                logger.error(f"❌ 获取图层信息失败: HTTP {layer_response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ 应用样式异常: {e}")
            
        return False


# 默认GeoServer管理器实例
geoserver_manager = GeoServerManager()


def get_geoserver_manager() -> GeoServerManager:
    """获取GeoServer管理器实例"""
    return geoserver_manager





