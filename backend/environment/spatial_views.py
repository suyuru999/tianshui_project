"""
地理空间服务视图
提供WMS、WFS、WCS等OGC标准服务接口
"""

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from django.utils import timezone
import logging
import json
import os

from .geoserver_config import get_geoserver_manager
from .models import BusinessLayer, RemoteSensingImage, EcologicalIndex

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([])
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
@authentication_classes([])
@permission_classes([AllowAny])
def wms_map(request):
    """WMS地图服务"""
    try:
        geoserver = get_geoserver_manager()
        import requests
        upstream = requests.get(
            f"{geoserver.base_url}/ows",
            params=request.GET,
            auth=geoserver.auth,
            timeout=120,
        )
        return HttpResponse(
            upstream.content,
            status=upstream.status_code,
            content_type=upstream.headers.get('Content-Type', 'application/octet-stream')
        )
        
    except Exception as e:
        logger.error(f"WMS地图服务失败: {e}")
        return Response(
            {'error': f'WMS地图服务失败: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([])
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
@authentication_classes([])
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
@permission_classes([IsAuthenticated])
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
@authentication_classes([])
@permission_classes([AllowAny])
def geoserver_status(request):
    """获取GeoServer状态"""
    try:
        geoserver = get_geoserver_manager()
        
        # 测试连接
        capabilities = geoserver.get_wms_capabilities()
        
        # 尝试创建工作空间验证权限
        workspace_ok = False
        try:
            workspace_ok = geoserver.create_workspace()
        except:
            pass
        
        status_info = {
            'connected': capabilities is not None,
            'base_url': geoserver.base_url,
            'workspace': geoserver.workspace,
            'workspace_ready': workspace_ok,
            'wms_enabled': capabilities is not None,
            'wfs_enabled': True,
            'wcs_enabled': True,
            'configured': True
        }
        
        return Response({
            'message': '获取GeoServer状态成功',
            'status': status_info,
            'tips': {
                'connected': 'GeoServer连接正常' if capabilities else 'GeoServer未连接，请检查配置和运行状态',
                'workspace': f'工作空间 "{geoserver.workspace}" {"已就绪" if workspace_ok else "需要创建"}',
                'next_steps': [] if capabilities else [
                    '1. 确认GeoServer已启动（访问 http://localhost:8080/geoserver）',
                    '2. 检查配置的URL、用户名、密码是否正确',
                    '3. 运行命令测试：python manage.py test_geoserver'
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"获取GeoServer状态失败: {e}")
        status_info = {
            'connected': False,
            'base_url': getattr(get_geoserver_manager(), 'base_url', '未配置'),
            'workspace': getattr(get_geoserver_manager(), 'workspace', '未配置'),
            'error': str(e)
        }
        
        return Response({
            'message': '获取GeoServer状态失败',
            'status': status_info,
            'error': str(e),
            'tips': {
                'error': '无法连接到GeoServer',
                'checklist': [
                    '确认GeoServer是否已安装并启动',
                    '检查URL是否正确（默认：http://localhost:8080/geoserver）',
                    '验证用户名和密码是否正确',
                    '查看后端日志了解更多信息'
                ]
            }
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """Return deployment health checks for database, media storage and GeoServer."""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['database'] = {'ok': True, 'message': '数据库连接正常'}
    except Exception as exc:
        checks['database'] = {'ok': False, 'message': f'数据库连接失败: {exc}'}

    media_root = str(settings.MEDIA_ROOT)
    checks['media_root'] = {
        'ok': os.path.isdir(media_root) and os.access(media_root, os.W_OK),
        'path': media_root,
        'message': '媒体目录可写' if os.path.isdir(media_root) and os.access(media_root, os.W_OK) else '媒体目录不存在或不可写',
    }

    try:
        geoserver = get_geoserver_manager()
        capabilities = geoserver.get_wms_capabilities()
        workspace_ready = False
        if capabilities:
            try:
                workspace_ready = bool(geoserver.create_workspace())
            except Exception:
                workspace_ready = False
        checks['geoserver'] = {
            'ok': bool(capabilities) and workspace_ready,
            'connected': bool(capabilities),
            'workspace_ready': workspace_ready,
            'workspace': geoserver.workspace,
            'base_url': geoserver.base_url,
            'message': 'GeoServer连接和工作空间正常' if capabilities and workspace_ready else 'GeoServer未连接或工作空间未就绪',
        }
    except Exception as exc:
        checks['geoserver'] = {'ok': False, 'message': f'GeoServer检测失败: {exc}'}

    layer_counts = {
        'total': BusinessLayer.objects.count(),
        'published': BusinessLayer.objects.filter(status='published').count(),
        'failed': BusinessLayer.objects.filter(status='failed').count(),
        'uploaded': BusinessLayer.objects.filter(status='uploaded').count(),
    }
    checks['business_layers'] = {
        'ok': layer_counts['failed'] == 0,
        'counts': layer_counts,
        'message': '业务图层状态正常' if layer_counts['failed'] == 0 else f"存在 {layer_counts['failed']} 个发布失败图层",
    }

    overall_ok = all(item.get('ok') for item in checks.values())
    return Response({
        'ok': overall_ok,
        'checked_at': timezone.now(),
        'checks': checks,
    }, status=status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE)





