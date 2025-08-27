"""
地理空间服务视图
提供WMS、WFS、WCS等OGC标准服务接口
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
import logging
import json

from .geoserver_config import get_geoserver_manager
from .models import RemoteSensingImage, EcologicalIndex

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def wms_capabilities(request):
    """获取WMS服务能力"""
    try:
        geoserver = get_geoserver_manager()
        capabilities = geoserver.get_wms_capabilities()
        
        if capabilities:
            return HttpResponse(capabilities, content_type='application/xml')
        else:
            return Response(
                {'error': '无法获取WMS服务能力'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception as e:
        logger.error(f"获取WMS能力失败: {e}")
        return Response(
            {'error': f'获取WMS能力失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def wms_map(request):
    """WMS地图服务"""
    try:
        # 获取请求参数
        service = request.GET.get('SERVICE', 'WMS')
        version = request.GET.get('VERSION', '1.3.0')
        request_type = request.GET.get('REQUEST', 'GetMap')
        layers = request.GET.get('LAYERS', '')
        styles = request.GET.get('STYLES', '')
        crs = request.GET.get('CRS', 'EPSG:4326')
        bbox = request.GET.get('BBOX', '')
        width = request.GET.get('WIDTH', '256')
        height = request.GET.get('HEIGHT', '256')
        format = request.GET.get('FORMAT', 'image/png')
        
        # 构建GeoServer WMS请求
        geoserver = get_geoserver_manager()
        wms_url = f"{geoserver.base_url}/ows"
        
        # 这里应该转发请求到GeoServer
        # 由于复杂性，这里只返回参数信息
        return Response({
            'message': 'WMS请求参数',
            'parameters': {
                'service': service,
                'version': version,
                'request': request_type,
                'layers': layers,
                'styles': styles,
                'crs': crs,
                'bbox': bbox,
                'width': width,
                'height': height,
                'format': format
            }
        })
        
    except Exception as e:
        logger.error(f"WMS地图服务失败: {e}")
        return Response(
            {'error': f'WMS地图服务失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def wfs_capabilities(request):
    """获取WFS服务能力"""
    try:
        geoserver = get_geoserver_manager()
        # 构建WFS能力请求URL
        wfs_url = f"{geoserver.base_url}/ows?service=WFS&version=2.0.0&request=GetCapabilities"
        
        return Response({
            'message': 'WFS服务能力',
            'wfs_url': wfs_url,
            'supported_operations': [
                'GetCapabilities',
                'DescribeFeatureType',
                'GetFeature',
                'Transaction'
            ]
        })
        
    except Exception as e:
        logger.error(f"获取WFS能力失败: {e}")
        return Response(
            {'error': f'获取WFS能力失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def spatial_layers(request):
    """获取可用的空间图层列表"""
    try:
        # 获取遥感影像图层 - 科研展示版本，返回所有数据
        remote_sensing_images = RemoteSensingImage.objects.all().values('id', 'name', 'image_type', 'center_lat', 'center_lon')
        
        # 获取生态指数图层 - 科研展示版本，返回所有数据
        ecological_indices = EcologicalIndex.objects.all().values(
            'id', 'index_type', 'remote_sensing_image__name', 
            'remote_sensing_image__center_lat', 'remote_sensing_image__center_lon'
        )
        
        layers = {
            'remote_sensing': list(remote_sensing_images),
            'ecological_indices': list(ecological_indices)
        }
        
        return Response({
            'message': '获取空间图层成功',
            'layers': layers
        })
        
    except Exception as e:
        logger.error(f"获取空间图层失败: {e}")
        return Response(
            {'error': f'获取空间图层失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def publish_to_geoserver(request):
    """发布图层到GeoServer"""
    try:
        layer_id = request.data.get('layer_id')
        layer_type = request.data.get('layer_type')  # 'remote_sensing' 或 'ecological_indices'
        datastore_name = request.data.get('datastore_name')
        
        if not all([layer_id, layer_type, datastore_name]):
            return Response(
                {'error': '缺少必要参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        geoserver = get_geoserver_manager()
        
        # 根据图层类型获取数据
        if layer_type == 'remote_sensing':
            layer_obj = RemoteSensingImage.objects.get(id=layer_id)  # 科研展示版本，不检查用户
            file_path = layer_obj.file_path.path
            layer_name = f"rs_{layer_obj.name}"
        elif layer_type == 'ecological_indices':
            layer_obj = EcologicalIndex.objects.get(id=layer_id)  # 科研展示版本，不检查用户
            file_path = layer_obj.result_file.path
            layer_name = f"ei_{layer_obj.remote_sensing_image.name}"
        else:
            return Response(
                {'error': '不支持的图层类型'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 确保工作空间存在
        geoserver.create_workspace()
        
        # 创建数据存储
        if not geoserver.create_datastore(datastore_name):
            return Response(
                {'error': '创建数据存储失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 发布图层
        if geoserver.publish_raster(datastore_name, layer_name, file_path):
            return Response({
                'message': '图层发布成功',
                'layer_name': layer_name,
                'wms_url': f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}"
            })
        else:
            return Response(
                {'error': '图层发布失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except RemoteSensingImage.DoesNotExist:
        return Response(
            {'error': '遥感影像不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except EcologicalIndex.DoesNotExist:
        return Response(
            {'error': '生态指数不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"发布图层到GeoServer失败: {e}")
        return Response(
            {'error': f'发布图层失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def geoserver_status(request):
    """获取GeoServer状态"""
    try:
        geoserver = get_geoserver_manager()
        
        # 测试连接
        capabilities = geoserver.get_wms_capabilities()
        
        status_info = {
            'connected': capabilities is not None,
            'base_url': geoserver.base_url,
            'workspace': geoserver.workspace,
            'wms_enabled': True,
            'wfs_enabled': True,
            'wcs_enabled': True
        }
        
        return Response({
            'message': '获取GeoServer状态成功',
            'status': status_info
        })
        
    except Exception as e:
        logger.error(f"获取GeoServer状态失败: {e}")
        return Response(
            {'error': f'获取GeoServer状态失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





