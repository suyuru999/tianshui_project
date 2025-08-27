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
        datastore_data = {
            "dataStore": {
                "name": datastore_name,
                "type": datastore_type,
                "enabled": True
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
        return False
    
    def publish_raster(self, datastore_name: str, layer_name: str, file_path: str) -> bool:
        """发布栅格图层"""
        # 上传文件到GeoServer
        upload_url = f"{self.base_url}/rest/workspaces/{self.workspace}/datastores/{datastore_name}/file.geotiff"
        
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(
                    upload_url,
                    auth=self.auth,
                    data=f,
                    headers={'Content-Type': 'image/tiff'}
                )
            
            if response.status_code in [200, 201]:
                # 创建图层
                layer_data = {
                    "layer": {
                        "name": layer_name,
                        "type": "RASTER",
                        "defaultStyle": {
                            "name": "raster"
                        }
                    }
                }
                
                result = self._make_request(
                    'POST',
                    f'workspaces/{self.workspace}/datastores/{datastore_name}/layers',
                    json=layer_data
                )
                
                if result is not None:
                    logger.info(f"栅格图层 {layer_name} 发布成功")
                    return True
            else:
                logger.error(f"文件上传失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"发布栅格图层失败: {e}")
            
        return False
    
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


# 默认GeoServer管理器实例
geoserver_manager = GeoServerManager()


def get_geoserver_manager() -> GeoServerManager:
    """获取GeoServer管理器实例"""
    return geoserver_manager





