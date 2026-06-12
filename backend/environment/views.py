from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import get_valid_filename
import os
import json
import logging
import requests
import time
import uuid
import re
import zipfile
import numpy as np
import rasterio
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# 取消注释必要的导入
from .models import (
    RemoteSensingImage,
    EcologicalIndex,
    RSEIResult,
    ProcessingTask,
    CitizenFeedback,
    ClimateDataFile,
    ClimateAnalysisResult,
    BusinessLayer,
    BusinessLayerAuditLog,
    EcologicalIndexFile,
    EcologicalProjectFile,
    OverlayAnalysisTask
)
from .serializers import (
    RemoteSensingImageSerializer,
    EcologicalIndexSerializer,
    RSEIResultSerializer,
    ProcessingTaskSerializer,
    RemoteSensingImageUploadSerializer,
    EcologicalIndexCalculationSerializer,
    RSEICalculationSerializer,
    CitizenFeedbackSerializer,
    ClimateDataFileSerializer,
    ClimateDataFileUploadSerializer,
    ClimateAnalysisResultSerializer,
    ClimateAnalysisRequestSerializer,
    BusinessLayerSerializer,
    BusinessLayerStyleSerializer,
    BusinessLayerAuditLogSerializer,
    BusinessLayerServiceSerializer,
    BusinessLayerUploadSerializer,
    EcologicalIndexFileSerializer,
    EcologicalIndexFileUploadSerializer,
    EcologicalProjectFileSerializer,
    EcologicalProjectFileUploadSerializer,
    OverlayAnalysisTaskSerializer,
    OverlayAnalysisTaskCreateSerializer
)
from .tasks import calculate_ecological_indices, calculate_rsei_only
from .ecological_indices import EcologicalIndexCalculator
from .raster_processing import (
    calculate_normalized_index_windowed,
    calculate_normalized_index_preview_stats,
    prepare_raster_upload,
    preview_array,
    raster_band_statistics,
    remove_tree,
    RasterioLandUseAnalyzer,
    validate_shapefile_zip,
)
try:
    from .gdal_land_use_analysis import LandUseAnalyzer
    from .vector_rasterize import rasterize_shapefile_to_tiff
    GDAL_IMPORT_ERROR = None
except ImportError as exc:
    LandUseAnalyzer = None
    rasterize_shapefile_to_tiff = None
    GDAL_IMPORT_ERROR = exc
from .file_utils import safe_file_cleanup, get_cleanup_files

logger = logging.getLogger(__name__)

# 取消注释遥感影像视图集
class RemoteSensingImageViewSet(viewsets.ModelViewSet):
    """遥感影像视图集"""
    queryset = RemoteSensingImage.objects.all()
    serializer_class = RemoteSensingImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]  # 修改为允许所有请求
    
    def get_serializer_class(self):
        """根据操作选择序列化器"""
        if self.action == 'create':
            return RemoteSensingImageUploadSerializer
        return RemoteSensingImageSerializer
    
    def perform_create(self, serializer):
        """创建时设置上传用户"""
        # 如果用户已认证，则设置上传用户，否则设为None
        if self.request.user.is_authenticated:
            serializer.save(uploaded_by=self.request.user)
        else:
            serializer.save(uploaded_by=None)
    
    @action(detail=True, methods=['post'])
    def calculate_indices(self, request, pk=None):
        """计算生态指数"""
        try:
            # 添加调试信息
            print(f"收到计算请求，影像ID: {pk}")
            print(f"请求方法: {request.method}")
            print(f"请求内容类型: {request.content_type}")
            print(f"请求数据: {request.data}")

            image = self.get_object()
            print(f"找到影像: {image.name}")

            # 获取要计算的指数类型
            indices_list = request.data.get('indices', ['ndvi', 'ndwi', 'ndbi'])
            print(f"请求的指数类型: {indices_list}")

            # 标准化指数类型名称（转换为小写）
            normalized_indices = [idx.lower() for idx in indices_list]
            print(f"标准化后的指数类型: {normalized_indices}")

            # 验证指数类型
            valid_indices = ['ndvi', 'ndwi', 'ndbi', 'ndsi', 'wetness', 'dryness', 'heat', 'greenness']
            if not all(idx in valid_indices for idx in normalized_indices):
                error_msg = f'不支持的指数类型。支持的指数: {", ".join(valid_indices)}'
                print(f"验证失败: {error_msg}")
                return Response({
                    'error': error_msg
                }, status=400)

            print(f"指数类型验证通过，开始创建任务")

            # 创建处理任务
            task = ProcessingTask.objects.create(
                remote_sensing_image=image,
                task_type=f'生态指数计算 - {", ".join(normalized_indices)}',
                status='pending',
                created_by=request.user if request.user.is_authenticated else None
            )

            print(f"任务创建成功，任务ID: {task.id}")
            # 启动Celery任务进行计算。开发环境下 Celery eager 模式会同步执行，
            # 生产环境配置 broker 后仍可异步执行。
            from .tasks import calculate_ecological_indices
            celery_task = calculate_ecological_indices.delay(str(image.id), normalized_indices, str(task.id))
            
            task.refresh_from_db()
            print(f"Celery任务启动成功，任务ID: {celery_task.id}")

            return Response({
                'message': '生态指数计算已启动',
                'task_id': str(task.id),
                'celery_task_id': str(celery_task.id),
                'indices': indices_list
            })

        except Exception as e:
            print(f"启动生态指数计算失败: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"启动生态指数计算失败: {e}")
            return Response({
                'error': f'启动计算失败: {str(e)}'
            }, status=500)

    @action(detail=True, methods=['get'])
    def indices(self, request, pk=None):
        """获取影像的生态指数列表及统计数据"""
        try:
            image = self.get_object()

            # 获取该影像的所有生态指数
            indices = EcologicalIndex.objects.filter(remote_sensing_image=image)

            if not indices.exists():
                response = Response({
                    'message': '该影像暂无生态指数数据',
                    'indices': []
                })
                response['Content-Type'] = 'application/json; charset=utf-8'
                return response

            # 序列化数据
            serializer = EcologicalIndexSerializer(indices, many=True)

            # 手动添加正确的中文显示文本
            indices_data = serializer.data
            for index_data in indices_data:
                # 修复index_type_display
                index_type = index_data.get('index_type', '')
                index_type_display_map = {
                    'ndvi': 'NDVI - 归一化植被指数',
                    'ndwi': 'NDWI - 归一化水体指数',
                    'ndbi': 'NDBI - 归一化建筑指数',
                    'ndsi': 'NDSI - 归一化积雪指数',
                    'rsei': 'RSEI - 遥感生态指数',
                    'wetness': '湿度指数',
                    'dryness': '干度指数',
                    'heat': '热度指数',
                    'greenness': '绿度指数',
                }
                index_data['index_type_display'] = index_type_display_map.get(index_type, index_type.upper())
                
                # 修复remote_sensing_image中的processing_status_display
                if 'remote_sensing_image' in index_data:
                    processing_status = index_data['remote_sensing_image'].get('processing_status', '')
                    status_display_map = {
                        'pending': '等待中',
                        'processing': '处理中',
                        'completed': '已完成',
                        'failed': '失败',
                    }
                    index_data['remote_sensing_image']['processing_status_display'] = status_display_map.get(processing_status, processing_status)

            response = Response({
                'message': '获取生态指数成功',
                'count': indices.count(),
                'indices': indices_data
            })
            response['Content-Type'] = 'application/json; charset=utf-8'
            return response

        except Exception as e:
            logger.error(f"获取生态指数失败: {e}")
            response = Response({
                'error': f'获取生态指数失败: {str(e)}'
            }, status=500)
            response['Content-Type'] = 'application/json; charset=utf-8'
            return response


class EcologicalIndexViewSet(viewsets.ModelViewSet):
    """生态指数视图集"""
    queryset = EcologicalIndex.objects.select_related('remote_sensing_image').all()
    serializer_class = EcologicalIndexSerializer
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """按影像ID创建生态指数计算任务"""
        serializer = EcologicalIndexCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_id = serializer.validated_data['remote_sensing_image_id']
        indices = serializer.validated_data['indices']
        image = get_object_or_404(RemoteSensingImage, id=image_id)
        
        task = ProcessingTask.objects.create(
            remote_sensing_image=image,
            task_type=f'生态指数计算 - {", ".join(indices)}',
            status='pending',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        celery_task = calculate_ecological_indices.delay(str(image.id), indices, str(task.id))
        
        return Response({
            'message': '生态指数计算已启动',
            'task_id': str(task.id),
            'celery_task_id': str(celery_task.id),
            'indices': indices
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """获取单个生态指数统计信息"""
        index = self.get_object()
        return Response({
            'id': str(index.id),
            'index_type': index.index_type,
            'index_type_display': index.get_index_type_display(),
            'min_value': index.min_value,
            'max_value': index.max_value,
            'mean_value': index.mean_value,
            'std_value': index.std_value,
            'excellent_area': index.excellent_area,
            'good_area': index.good_area,
            'moderate_area': index.moderate_area,
            'poor_area': index.poor_area,
            'bad_area': index.bad_area,
        })


class RSEIResultViewSet(viewsets.ModelViewSet):
    """RSEI结果视图集"""
    queryset = RSEIResult.objects.select_related(
        'remote_sensing_image',
        'greenness',
        'wetness',
        'dryness',
        'heat',
        'rsei_result'
    ).all()
    serializer_class = RSEIResultSerializer
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """按影像ID创建RSEI计算任务"""
        serializer = RSEICalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_id = serializer.validated_data['remote_sensing_image_id']
        celery_task = calculate_rsei_only.delay(str(image_id))
        
        return Response({
            'message': 'RSEI计算已启动',
            'celery_task_id': str(celery_task.id),
            'remote_sensing_image_id': str(image_id)
        }, status=status.HTTP_201_CREATED)

class ProcessingTaskViewSet(viewsets.ModelViewSet):
    """处理任务视图集"""
    queryset = ProcessingTask.objects.all()
    serializer_class = ProcessingTaskSerializer
    permission_classes = [permissions.AllowAny]  # 允许所有请求
    
    def perform_create(self, serializer):
        """创建时设置创建用户"""
        # 如果用户已认证，则设置创建用户，否则设为None
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save(created_by=None)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取任务状态"""
        task = self.get_object()
        return Response({
            'id': task.id,
            'status': task.status,
            'status_display': task.get_status_display(),
            'progress': task.progress,
            'current_step': task.current_step,
            'error_message': task.error_message,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at
        })

class CitizenFeedbackViewSet(viewsets.ModelViewSet):
    """民众意见反馈视图集"""
    queryset = CitizenFeedback.objects.all()
    serializer_class = CitizenFeedbackSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save(created_by=None)

    @action(detail=False, methods=['delete'], url_path='clear')
    def clear(self, request):
        deleted_count = self.get_queryset().count()
        self.get_queryset().delete()
        return Response({
            'message': '反馈记录已清空',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)


REMOTE_INDEX_METHODS = {
    'ndvi': ('NDVI', 'calculate_ndvi'),
    'ndwi': ('NDWI', 'calculate_ndwi'),
    'ndbi': ('NDBI', 'calculate_ndbi'),
    'dryness': ('干度指数', 'calculate_dryness'),
    'wetness': ('湿度指数', 'calculate_wetness'),
    'heat': ('热度指数', 'calculate_heat'),
    'greenness': ('绿度指数', 'calculate_greenness'),
}


REMOTE_INDEX_LABELS = {
    'ndvi': '绿化指数(NDVI)',
    'ndwi': '湿度指数(NDWI)',
    'ndbi': '建筑指数(NDBI)',
    'dryness': '干度指数(NDBSI)',
    'wetness': '湿度指数(Tasseled Cap)',
    'heat': '热度指数(LST/Heat)',
    'greenness': '绿度指数',
    'rsei': '遥感生态指数(RSEI)',
}


def _supported_remote_indices(band_count):
    if band_count is None:
        return sorted([*REMOTE_INDEX_METHODS.keys(), 'rsei'])
    if band_count == 1:
        return ['uploaded_raster']
    if band_count >= 6:
        return sorted([*REMOTE_INDEX_METHODS.keys(), 'rsei'])
    if band_count == 5:
        return ['ndvi', 'ndwi']
    if band_count == 4:
        return ['ndvi', 'ndwi']
    if band_count == 3:
        return ['ndvi', 'ndwi', 'ndbi']
    return []


def _unsupported_remote_index_response(index_type, band_count):
    supported_indices = _supported_remote_indices(band_count)
    requested_label = REMOTE_INDEX_LABELS.get(index_type, index_type.upper())
    supported_labels = [
        REMOTE_INDEX_LABELS.get(item, item.upper())
        for item in supported_indices
        if item != 'uploaded_raster'
    ]

    if band_count == 4:
        detail = (
            f'当前影像为4波段，不支持{requested_label}。'
            '这类GF/PMS四波段影像通常可计算NDVI或NDWI；'
            '热度指数、干度指数和RSEI需要包含短波红外/热红外等更多有效波段的数据。'
        )
    elif band_count and band_count < 6:
        detail = (
            f'当前影像为{band_count}波段，不支持{requested_label}。'
            '请改选该影像支持的指数，或上传包含至少6个有效波段的多光谱影像。'
        )
    else:
        detail = f'当前影像不支持{requested_label}，请检查影像波段配置。'

    return Response({
        'error': detail,
        'bands_count': band_count,
        'requested_index': index_type,
        'supported_indices': supported_indices,
        'supported_index_labels': supported_labels,
    }, status=400)


def _save_uploaded_file(uploaded_file, subdir):
    safe_name = get_valid_filename(uploaded_file.name)
    relative_path = os.path.join(subdir, f'{uuid.uuid4().hex}_{safe_name}')
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    with open(absolute_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return relative_path.replace('\\', '/'), absolute_path


def _media_url(request, relative_path):
    if not relative_path:
        return None
    url = settings.MEDIA_URL + relative_path.replace('\\', '/')
    return request.build_absolute_uri(url)


def _statistics_payload(stats):
    return {
        'min_value': stats.get('min_value') if stats else None,
        'max_value': stats.get('max_value') if stats else None,
        'mean_value': stats.get('mean_value') if stats else None,
        'std_value': stats.get('std_value') if stats else None,
        'excellent_area': stats.get('excellent_area') if stats else None,
        'good_area': stats.get('good_area') if stats else None,
        'moderate_area': stats.get('moderate_area') if stats else None,
        'poor_area': stats.get('poor_area') if stats else None,
        'bad_area': stats.get('bad_area') if stats else None,
    }


def _single_band_statistics(path):
    return preview_array(path), raster_band_statistics(path)


def _safe_layer_name(name):
    base = re.sub(r'[^0-9A-Za-z_]+', '_', name or '').strip('_').lower()
    if not base:
        base = 'business_layer'
    if base[0].isdigit():
        base = f'layer_{base}'
    return f'{base}_{uuid.uuid4().hex[:8]}'


def _build_ogc_urls(geoserver, layer_name, layer_type):
    qualified_layer = f'{geoserver.workspace}:{layer_name}'
    base_ows = f'{geoserver.base_url}/ows'
    urls = {
        'wms_url': (
            f'{base_ows}?service=WMS&version=1.3.0&request=GetMap'
            f'&layers={qualified_layer}&format=image/png&transparent=true'
        )
    }
    if layer_type == 'vector':
        urls['wfs_url'] = (
            f'{base_ows}?service=WFS&version=2.0.0&request=GetFeature'
            f'&typeNames={qualified_layer}&outputFormat=application/json'
        )
        urls['wcs_url'] = None
    else:
        urls['wfs_url'] = None
        urls['wcs_url'] = (
            f'{base_ows}?service=WCS&version=2.0.1&request=GetCoverage'
            f'&coverageId={qualified_layer}'
        )
    return urls


def _raster_layer_metadata(path):
    """读取栅格基础元数据，供前端定位和服务说明使用。"""
    metadata = {}
    try:
        with rasterio.open(path) as dataset:
            bounds = dataset.bounds
            metadata.update({
                'bounds': [bounds.left, bounds.bottom, bounds.right, bounds.top],
                'crs': dataset.crs.to_string() if dataset.crs else None,
                'width': dataset.width,
                'height': dataset.height,
                'band_count': dataset.count,
                'dtype': dataset.dtypes[0] if dataset.dtypes else None,
            })
    except Exception as exc:
        logger.warning(f"读取栅格元数据失败: {exc}")
    return metadata


def _vector_layer_metadata(path):
    """读取矢量基础元数据，供前端定位和服务说明使用。"""
    metadata = {}
    try:
        from osgeo import ogr
        datasource = ogr.Open(path)
        if datasource is None:
            return metadata

        layer = datasource.GetLayer(0)
        extent = layer.GetExtent()
        spatial_ref = layer.GetSpatialRef()
        crs = None
        if spatial_ref:
            auth_name = spatial_ref.GetAuthorityName(None)
            auth_code = spatial_ref.GetAuthorityCode(None)
            if auth_name and auth_code:
                crs = f'{auth_name}:{auth_code}'
            else:
                crs = spatial_ref.ExportToWkt()

        if extent:
            min_x, max_x, min_y, max_y = extent
            metadata['bounds'] = [min_x, min_y, max_x, max_y]
        metadata['crs'] = crs or 'EPSG:4326'
        metadata['feature_count'] = layer.GetFeatureCount()
        datasource = None
    except Exception as exc:
        logger.warning(f"读取矢量元数据失败: {exc}")
    return metadata


def _extract_shapefile_zip(zip_path, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            normalized = member.filename.replace('\\', '/')
            if normalized.startswith('/') or '..' in normalized.split('/'):
                raise ValueError('ZIP文件中包含不安全路径')
        zip_ref.extractall(target_dir)

    shp_files = []
    for root, _, files in os.walk(target_dir):
        for file_name in files:
            if file_name.lower().endswith('.shp'):
                shp_files.append(os.path.join(root, file_name))
    if not shp_files:
        raise ValueError('ZIP文件中未找到.shp文件')
    return shp_files[0]


def _convert_kml_to_shapefile(kml_path, target_dir, output_name):
    os.makedirs(target_dir, exist_ok=True)
    try:
        from osgeo import ogr
    except ImportError as exc:
        raise RuntimeError('当前环境缺少 GDAL/OGR，无法将 KML 转换为 Shapefile') from exc

    data_source = ogr.Open(kml_path)
    if data_source is None:
        raise ValueError('KML 文件无法读取，请检查文件内容是否完整')

    source_layer = None
    for index in range(data_source.GetLayerCount()):
        candidate = data_source.GetLayerByIndex(index)
        if candidate and candidate.GetFeatureCount() > 0:
            source_layer = candidate
            break
    if source_layer is None:
        source_layer = data_source.GetLayer(0)
    if source_layer is None:
        raise ValueError('KML 文件中未找到可转换的图层')

    shapefile_path = os.path.join(target_dir, f'{output_name}.shp')
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(shapefile_path):
        driver.DeleteDataSource(shapefile_path)

    target_ds = driver.CreateDataSource(shapefile_path)
    if target_ds is None:
        raise RuntimeError('创建 Shapefile 失败')

    source_srs = source_layer.GetSpatialRef()
    geometry_type = source_layer.GetGeomType()
    target_layer = target_ds.CreateLayer(output_name, srs=source_srs, geom_type=geometry_type)
    layer_defn = source_layer.GetLayerDefn()

    for field_index in range(layer_defn.GetFieldCount()):
        field_defn = layer_defn.GetFieldDefn(field_index)
        target_layer.CreateField(field_defn)

    target_defn = target_layer.GetLayerDefn()
    source_layer.ResetReading()
    for feature in source_layer:
        target_feature = ogr.Feature(target_defn)
        target_feature.SetFrom(feature)
        geometry = feature.GetGeometryRef()
        if geometry is not None:
            target_feature.SetGeometry(geometry.Clone())
        if target_layer.CreateFeature(target_feature) != 0:
            raise RuntimeError('KML 转换写入 Shapefile 失败')
        target_feature = None

    data_source = None
    target_ds = None

    cpg_path = os.path.splitext(shapefile_path)[0] + '.cpg'
    with open(cpg_path, 'w', encoding='utf-8') as cpg_file:
        cpg_file.write('UTF-8')

    return shapefile_path


def _update_url_query(url, **params):
    parsed = urlsplit(url)
    query = {key: value for key, value in parse_qsl(parsed.query, keep_blank_values=True)}
    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _service_health_payload(status_value='unknown', message=None):
    return {
        'service_health_status': status_value,
        'service_health_message': message,
        'service_checked_at': timezone.now(),
    }


def _hex_to_rgb(color):
    color = (color or '').strip().lstrip('#')
    if len(color) != 6:
        raise ValueError('颜色值必须是 6 位十六进制')
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _interpolate_color(start_color, end_color, factor):
    start_rgb = _hex_to_rgb(start_color)
    end_rgb = _hex_to_rgb(end_color)
    rgb = tuple(round(start_rgb[index] + (end_rgb[index] - start_rgb[index]) * factor) for index in range(3))
    return f'#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}'


def _log_business_layer_action(layer, action, status_value='info', message=None, operator=None, details=None):
    operator_name = None
    if operator and getattr(operator, 'is_authenticated', False):
        operator_name = operator.username
    elif layer.uploaded_by:
        operator_name = layer.uploaded_by.username

    return BusinessLayerAuditLog.objects.create(
        business_layer=layer,
        action=action,
        status=status_value,
        operator=operator if operator and getattr(operator, 'is_authenticated', False) else None,
        operator_name=operator_name,
        message=message,
        details=details or {},
    )


def _vector_style_sld(layer_name, style_config):
    fill_color = style_config.get('fill_color') or '#1f8f4d'
    stroke_color = style_config.get('stroke_color') or fill_color
    stroke_width = style_config.get('stroke_width', 2)
    fill_opacity = style_config.get('fill_opacity', 0.18)
    classification_field = (style_config.get('classification_field') or '').strip()
    color_scheme = style_config.get('color_scheme') or 'green_yellow_red'
    geometry_type = (style_config.get('geometry_type') or 'polygon').lower()

    if classification_field and style_config.get('min_value') is not None and style_config.get('max_value') is not None:
        min_val = float(style_config['min_value'])
        max_val = float(style_config['max_value'])
        if max_val <= min_val:
            max_val = min_val + 1
        threshold1 = min_val + (max_val - min_val) * 0.33
        threshold2 = min_val + (max_val - min_val) * 0.67
        schemes = {
            'green_yellow_red': ('#2E8B57', '#F6C344', '#D64545'),
            'blue_cyan_green': ('#315f8c', '#4fb7c5', '#1f8f4d'),
            'purple_pink_red': ('#7c5cc4', '#d17ab4', '#d64545'),
        }
        low_color, mid_color, high_color = schemes.get(color_scheme, schemes['green_yellow_red'])
        symbolizer = f'''
          <Rule>
            <Name>low</Name>
            <ogc:Filter>
              <ogc:PropertyIsLessThan>
                <ogc:PropertyName>{classification_field}</ogc:PropertyName>
                <ogc:Literal>{threshold1:.6f}</ogc:Literal>
              </ogc:PropertyIsLessThan>
            </ogc:Filter>
            <PolygonSymbolizer>
              <Fill><CssParameter name="fill">{low_color}</CssParameter><CssParameter name="fill-opacity">{fill_opacity}</CssParameter></Fill>
              <Stroke><CssParameter name="stroke">{stroke_color}</CssParameter><CssParameter name="stroke-width">{stroke_width}</CssParameter></Stroke>
            </PolygonSymbolizer>
          </Rule>
          <Rule>
            <Name>medium</Name>
            <ogc:Filter>
              <ogc:And>
                <ogc:PropertyIsGreaterThanOrEqualTo>
                  <ogc:PropertyName>{classification_field}</ogc:PropertyName>
                  <ogc:Literal>{threshold1:.6f}</ogc:Literal>
                </ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyIsLessThan>
                  <ogc:PropertyName>{classification_field}</ogc:PropertyName>
                  <ogc:Literal>{threshold2:.6f}</ogc:Literal>
                </ogc:PropertyIsLessThan>
              </ogc:And>
            </ogc:Filter>
            <PolygonSymbolizer>
              <Fill><CssParameter name="fill">{mid_color}</CssParameter><CssParameter name="fill-opacity">{fill_opacity}</CssParameter></Fill>
              <Stroke><CssParameter name="stroke">{stroke_color}</CssParameter><CssParameter name="stroke-width">{stroke_width}</CssParameter></Stroke>
            </PolygonSymbolizer>
          </Rule>
          <Rule>
            <Name>high</Name>
            <ogc:Filter>
              <ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyName>{classification_field}</ogc:PropertyName>
                <ogc:Literal>{threshold2:.6f}</ogc:Literal>
              </ogc:PropertyIsGreaterThanOrEqualTo>
            </ogc:Filter>
            <PolygonSymbolizer>
              <Fill><CssParameter name="fill">{high_color}</CssParameter><CssParameter name="fill-opacity">{fill_opacity}</CssParameter></Fill>
              <Stroke><CssParameter name="stroke">{stroke_color}</CssParameter><CssParameter name="stroke-width">{stroke_width}</CssParameter></Stroke>
            </PolygonSymbolizer>
          </Rule>'''
    elif geometry_type == 'point':
        symbolizer = f'''
          <Rule>
            <PointSymbolizer>
              <Graphic>
                <Mark>
                  <WellKnownName>circle</WellKnownName>
                  <Fill><CssParameter name="fill">{fill_color}</CssParameter></Fill>
                  <Stroke><CssParameter name="stroke">{stroke_color}</CssParameter><CssParameter name="stroke-width">{stroke_width}</CssParameter></Stroke>
                </Mark>
                <Size>10</Size>
              </Graphic>
            </PointSymbolizer>
          </Rule>'''
    elif geometry_type == 'line':
        symbolizer = f'''
          <Rule>
            <LineSymbolizer>
              <Stroke>
                <CssParameter name="stroke">{stroke_color}</CssParameter>
                <CssParameter name="stroke-width">{stroke_width}</CssParameter>
              </Stroke>
            </LineSymbolizer>
          </Rule>'''
    else:
        symbolizer = f'''
          <Rule>
            <PolygonSymbolizer>
              <Fill><CssParameter name="fill">{fill_color}</CssParameter><CssParameter name="fill-opacity">{fill_opacity}</CssParameter></Fill>
              <Stroke><CssParameter name="stroke">{stroke_color}</CssParameter><CssParameter name="stroke-width">{stroke_width}</CssParameter></Stroke>
            </PolygonSymbolizer>
          </Rule>'''

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>{layer_name}</Name>
    <UserStyle>
      <Title>{layer_name} vector style</Title>
      <FeatureTypeStyle>{symbolizer}
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>'''


def _raster_style_sld(layer_name, style_config):
    opacity = style_config.get('raster_opacity', 0.72)
    min_value = float(style_config.get('min_value', 0))
    max_value = float(style_config.get('max_value', 100))
    if max_value <= min_value:
        max_value = min_value + 1
    ramp = style_config.get('raster_color_ramp') or 'green_yellow_red'
    ramps = {
        'green_yellow_red': ('#2E8B57', '#F6C344', '#D64545'),
        'blue_cyan_green': ('#315f8c', '#4fb7c5', '#1f8f4d'),
        'gray_blue': ('#6b7280', '#93c5fd', '#1d4ed8'),
    }
    start_color, mid_color, end_color = ramps.get(ramp, ramps['green_yellow_red'])
    q1 = min_value + (max_value - min_value) * 0.5
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>{layer_name}</Name>
    <UserStyle>
      <Title>{layer_name} raster style</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>{opacity}</Opacity>
            <ColorMap type="ramp">
              <ColorMapEntry color="{start_color}" quantity="{min_value:.6f}" opacity="{opacity}" />
              <ColorMapEntry color="{mid_color}" quantity="{q1:.6f}" opacity="{opacity}" />
              <ColorMapEntry color="{end_color}" quantity="{max_value:.6f}" opacity="{opacity}" />
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>'''


def _check_layer_service_availability(layer):
    timeout = 20

    try:
        if layer.layer_type == 'vector' and layer.wfs_url:
            type_name = layer.service_type_name or layer.geoserver_layer_name
            if layer.geoserver_workspace and type_name and ':' not in type_name and not layer.metadata.get('is_external_service'):
                type_name = f'{layer.geoserver_workspace}:{type_name}'
            probe_url = _update_url_query(
                layer.wfs_url,
                service='WFS',
                request='GetFeature',
                version='2.0.0',
                typeNames=type_name,
                outputFormat='application/json',
                count='1'
            )
            response = requests.get(probe_url, timeout=timeout)
            if response.ok:
                return _service_health_payload('healthy', 'WFS 服务可访问')
            return _service_health_payload('unhealthy', f'WFS 检测失败: HTTP {response.status_code}')

        if layer.wms_url:
            metadata = layer.metadata or {}
            bounds = metadata.get('bounds') or [-180, -90, 180, 90]
            crs = layer.service_srs or metadata.get('crs') or 'EPSG:4326'
            layers = layer.service_type_name or layer.geoserver_layer_name
            if layer.geoserver_workspace and layers and ':' not in layers and not metadata.get('is_external_service'):
                layers = f'{layer.geoserver_workspace}:{layers}'
            probe_url = _update_url_query(
                layer.wms_url,
                service='WMS',
                request='GetMap',
                version='1.1.0',
                layers=layers,
                bbox=','.join(str(value) for value in bounds),
                width='32',
                height='32',
                srs=crs,
                format='image/png',
                transparent='true'
            )
            response = requests.get(probe_url, timeout=timeout)
            if response.ok and 'image/' in (response.headers.get('Content-Type') or ''):
                return _service_health_payload('healthy', 'WMS 服务可访问')
            return _service_health_payload('unhealthy', f'WMS 检测失败: HTTP {response.status_code}')

        if layer.wcs_url:
            coverage_id = layer.service_type_name or layer.geoserver_layer_name
            if layer.geoserver_workspace and coverage_id and ':' not in coverage_id and not (layer.metadata or {}).get('is_external_service'):
                coverage_id = f'{layer.geoserver_workspace}:{coverage_id}'
            probe_url = _update_url_query(
                layer.wcs_url,
                service='WCS',
                request='DescribeCoverage',
                version='2.0.1',
                coverageId=coverage_id
            )
            response = requests.get(probe_url, timeout=timeout)
            if response.ok:
                return _service_health_payload('healthy', 'WCS 服务可访问')
            return _service_health_payload('unhealthy', f'WCS 检测失败: HTTP {response.status_code}')
    except requests.RequestException as exc:
        return _service_health_payload('unhealthy', f'服务检测异常: {exc}')
    except Exception as exc:
        return _service_health_payload('unhealthy', f'服务检测失败: {exc}')

    return _service_health_payload('unknown', '当前图层没有可检测的标准服务地址')


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def geoserver_ows_proxy(request):
    """代理GeoServer OWS服务，避免浏览器直接访问GeoServer时被CORS拦截。"""
    from .geoserver_config import get_geoserver_manager

    geoserver = get_geoserver_manager()
    try:
        upstream = requests.get(
            f'{geoserver.base_url}/ows',
            params=request.GET,
            auth=geoserver.auth,
            timeout=120,
        )
    except requests.RequestException as exc:
        return Response({'error': f'GeoServer代理请求失败: {exc}'}, status=502)

    content_type = upstream.headers.get('Content-Type', 'application/octet-stream')
    response = HttpResponse(
        upstream.content,
        status=upstream.status_code,
        content_type=content_type,
    )
    for header in ['Cache-Control', 'Expires', 'ETag', 'Last-Modified']:
        if upstream.headers.get(header):
            response[header] = upstream.headers[header]
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _landuse_visualization_payload(request, analyzer, source_file_name):
    result_dir_rel = f'landuse_results/{uuid.uuid4().hex}'
    result_dir_abs = os.path.join(settings.MEDIA_ROOT, result_dir_rel)
    os.makedirs(result_dir_abs, exist_ok=True)
    visualization_rel = f'{result_dir_rel}/land_use_visualization.png'
    visualization_abs = os.path.join(settings.MEDIA_ROOT, visualization_rel)
    analyzer.create_landuse_visualization(visualization_abs)
    return {
        'source_filename': source_file_name,
        'visualization_file_url': _media_url(request, visualization_rel),
        'landuse_statistics': analyzer.get_landuse_statistics(),
    }


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def analyze_remote_sensing_upload(request):
    """上传遥感/成果栅格并直接计算或统计展示，不要求先入库。"""
    if 'file' not in request.FILES:
        return Response({'error': '请上传 GeoTIFF 或常见影像文件'}, status=400)

    index_type = str(request.data.get('index_type') or 'ndvi').lower()
    if index_type == 'lst':
        index_type = 'heat'
    if index_type == 'ndbsi':
        index_type = 'dryness'

    uploaded_file = request.FILES['file']
    extension = os.path.splitext(uploaded_file.name.lower())[1]
    if extension == '.adf':
        return Response({
            'error': 'ADF 是 ArcGIS 栅格目录格式，不能作为单文件上传。请上传包含完整ADF文件夹的ZIP，或先转为GeoTIFF(.tif)。'
        }, status=400)
    if extension not in ['.tif', '.tiff', '.jpg', '.jpeg', '.png', '.zip']:
        return Response({'error': '仅支持 .tif/.tiff/.jpg/.jpeg/.png 或 ADF文件夹ZIP'}, status=400)

    upload_rel, upload_abs = _save_uploaded_file(uploaded_file, 'analysis_tmp')
    result_dir_rel = f'analysis_results/{uuid.uuid4().hex}'
    result_dir_abs = os.path.join(settings.MEDIA_ROOT, result_dir_rel)
    os.makedirs(result_dir_abs, exist_ok=True)

    calculator = None
    cleanup_dirs = []
    try:
        raster_abs = upload_abs
        if extension == '.zip':
            raster_abs, cleanup_dirs = prepare_raster_upload(upload_abs, result_dir_abs)
            extension = '.tif'

        if extension in ['.tif', '.tiff']:
            with rasterio.open(raster_abs) as probe_dataset:
                band_count = int(probe_dataset.count)
        else:
            band_count = None
        results = []
        supported_indices = _supported_remote_indices(band_count)
        if index_type not in supported_indices and band_count != 1:
            return _unsupported_remote_index_response(index_type, band_count)

        if band_count == 1 and extension in ['.tif', '.tiff']:
            label = '上传成果栅格'
            index_data, stats = _single_band_statistics(raster_abs)
            index_result_type = 'uploaded_raster'
        elif extension in ['.tif', '.tiff'] and index_type in ['ndvi', 'ndwi'] and band_count and band_count >= 3:
            index_result_type = index_type
            label = REMOTE_INDEX_METHODS[index_type][0]
            index_data, stats = calculate_normalized_index_preview_stats(raster_abs, index_type)
            result_file_url = None
        else:
            calculator = EcologicalIndexCalculator(raster_abs)
            if not calculator.load_image():
                return Response({'error': '影像加载失败，请检查文件格式、波段数或坐标信息'}, status=400)
            band_count = int(calculator.bands.shape[0])
            if index_type == 'rsei':
                rsei_result = calculator.calculate_rsei()
                if not rsei_result:
                    return _unsupported_remote_index_response(index_type, band_count)
                index_data = rsei_result['rsei']
                stats = calculator.calculate_statistics(index_data)
                label = 'RSEI'
                index_result_type = 'rsei'
            else:
                method_info = REMOTE_INDEX_METHODS.get(index_type)
                if not method_info:
                    return Response({
                        'error': f'不支持的指数类型: {index_type}',
                        'supported_indices': sorted([*REMOTE_INDEX_METHODS.keys(), 'rsei'])
                }, status=400)
                label, method_name = method_info
                index_data = getattr(calculator, method_name)()
                if index_data is None:
                    return _unsupported_remote_index_response(index_type, band_count)
                stats = calculator.calculate_statistics(index_data)
                index_result_type = index_type

        if not stats:
            return Response({'error': '统计结果生成失败'}, status=500)

        result_png_rel = f'{result_dir_rel}/{index_result_type}.png'
        result_png_abs = os.path.join(settings.MEDIA_ROOT, result_png_rel)
        result_file_url = locals().get('result_file_url')
        if calculator:
            result_tif_rel = f'{result_dir_rel}/{index_result_type}.tif'
            result_tif_abs = os.path.join(settings.MEDIA_ROOT, result_tif_rel)
            calculator.save_result(index_data, result_tif_abs)
            result_file_url = _media_url(request, result_tif_rel)

        preview_calculator = calculator or EcologicalIndexCalculator(raster_abs)
        preview_calculator.create_visualization(index_data, label, result_png_abs)

        results.append({
            'id': uuid.uuid4().hex,
            'index_type': index_result_type,
            'index_type_display': label,
            **_statistics_payload(stats),
            'result_file_url': result_file_url,
            'visualization_file_url': _media_url(request, result_png_rel),
        })

        return Response({
            'message': '分析完成',
            'source': {
                'filename': uploaded_file.name,
                'uploaded_file_url': _media_url(request, upload_rel),
                'bands_count': band_count,
                'supported_indices': _supported_remote_indices(band_count),
            },
            'indices': results,
            'result': results[0],
        })
    except Exception as exc:
        logger.exception('上传遥感影像分析失败')
        return Response({'error': f'分析失败: {exc}'}, status=500)
    finally:
        if calculator:
            calculator.close()
        try:
            if os.path.exists(upload_abs):
                os.remove(upload_abs)
        except Exception as cleanup_error:
            logger.warning(f'清理上传临时文件失败: {cleanup_error}')
        for cleanup_dir in cleanup_dirs:
            remove_tree(cleanup_dir)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def calculate_ecological_structure_indices(request):
    """
    计算生态环境结构指数
    包括：破碎度指数、内聚力指数、多样性指数、脆弱度指数
    """
    try:
        # 获取上传的土地利用数据文件
        if 'landuse_file' not in request.FILES:
            return Response({
                'error': '请上传土地利用数据文件'
            }, status=400)
        
        landuse_file = request.FILES['landuse_file']
        if landuse_file.name.lower().endswith('.adf'):
            return Response({
                'error': 'ADF 是 ArcGIS 栅格目录格式，不能作为单文件上传。请先用 GDAL/ArcGIS 转为 GeoTIFF(.tif) 后再上传。'
            }, status=400)
        
        # 保存文件到临时位置
        file_path = default_storage.save(
            f'landuse_analysis/{landuse_file.name}',
            ContentFile(landuse_file.read())
        )
        try:
            # 转换为绝对路径
            abs_file_path = default_storage.path(file_path)
            
            # 如果是矢量（.zip/.shp），先栅格化为整型GeoTIFF
            raster_input = abs_file_path
            lower = file_path.lower()
            if lower.endswith('.zip') or lower.endswith('.shp'):
                if GDAL_IMPORT_ERROR or rasterize_shapefile_to_tiff is None:
                    return Response({
                        'error': f'Shapefile栅格化需要 GDAL/osgeo。当前环境未安装: {GDAL_IMPORT_ERROR}'
                    }, status=503)
                # 选择分类字段：前端可传入 landuse_attr，否则尝试常见字段
                attr = request.data.get('landuse_attr') or 'class'
                try_fields = [attr, 'landuse', 'code', 'class_id']
                tmp_tif = os.path.splitext(abs_file_path)[0] + '.tif'
                last_err = None
                for field in try_fields:
                    try:
                        rasterize_shapefile_to_tiff(abs_file_path, tmp_tif, attribute_field=field)
                        raster_input = tmp_tif
                        break
                    except Exception as e:
                        last_err = e
                        continue
                else:
                    raise last_err or ValueError('栅格化失败，未找到有效属性字段')

            # 创建土地利用分析器
            analyzer_cls = LandUseAnalyzer if LandUseAnalyzer is not None else RasterioLandUseAnalyzer
            analyzer = analyzer_cls(raster_input)
            
            # 加载土地利用数据
            if not analyzer.load_landuse_data():
                return Response({
                    'error': '土地利用数据加载失败'
                }, status=400)
            
            # 计算各项生态环境结构指数
            results = {}
            
            # 1. 计算破碎度指数
            fragmentation_result = analyzer.calculate_fragmentation_index()
            if fragmentation_result:
                results['fragmentation'] = fragmentation_result
            else:
                results['fragmentation'] = {'error': '破碎度指数计算失败'}
            
            # 2. 计算内聚力指数
            cohesion_result = analyzer.calculate_cohesion_index()
            if cohesion_result:
                results['cohesion'] = cohesion_result
            else:
                results['cohesion'] = {'error': '内聚力指数计算失败'}
            
            # 3. 计算多样性指数
            diversity_result = analyzer.calculate_diversity_index()
            if diversity_result:
                results['diversity'] = diversity_result
            else:
                results['diversity'] = {'error': '多样性指数计算失败'}
            
            # 4. 计算脆弱度指数
            fragility_result = analyzer.calculate_fragility_index()
            if fragility_result:
                results['fragility'] = fragility_result
            else:
                results['fragility'] = {'error': '脆弱度指数计算失败'}

            visualization = _landuse_visualization_payload(request, analyzer, landuse_file.name)
            analyzer.close()
            
            # 清理临时文件
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except PermissionError:
                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            # 若生成了临时tif也清理
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:
                    os.remove(tif_candidate)
                except PermissionError:
                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
            
            return Response({
                'message': '生态环境结构指数计算完成',
                'results': results,
                'visualization': visualization,
                'summary': {
                    'fragmentation_index': results.get('fragmentation', {}).get('overall_fragmentation', 0),
                    'cohesion_index': results.get('cohesion', {}).get('cohesion_index', 0),
                    'shannon_diversity': results.get('diversity', {}).get('shannon_diversity', 0),
                    'fragility_index': results.get('fragility', {}).get('fragility_index', 0)
                }
            })
            
        except Exception as e:
            # 清理临时文件
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:

                    os.remove(abs_file_path)

                except PermissionError:

                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:

                    os.remove(tif_candidate)

                except PermissionError:

                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
            raise e
            
    except Exception as e:
        # 关闭分析器资源
        if 'analyzer' in locals():
            analyzer.close()
        
        # 清理临时文件
        try:
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except PermissionError:
                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:
                    os.remove(tif_candidate)
                except PermissionError:
                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件时出错: {cleanup_error}")
        
        logger.error(f"计算生态环境结构指数失败: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'计算失败: {str(e)}',
            'traceback': traceback.format_exc()
        }, status=500)

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def calculate_ecological_stress_indices(request):
    """
    计算生态环境胁迫指数
    包括：土壤侵蚀指数、未利用地面积比例、耕地建设用地面积比例、土地退化指数
    """
    try:
        # 获取上传的土地利用数据文件
        if 'landuse_file' not in request.FILES:
            return Response({
                'error': '请上传土地利用数据文件'
            }, status=400)
        
        landuse_file = request.FILES['landuse_file']
        if landuse_file.name.lower().endswith('.adf'):
            return Response({
                'error': 'ADF 是 ArcGIS 栅格目录格式，不能作为单文件上传。请先用 GDAL/ArcGIS 转为 GeoTIFF(.tif) 后再上传。'
            }, status=400)
        
        # 保存文件到临时位置
        file_path = default_storage.save(
            f'landuse_analysis/{landuse_file.name}',
            ContentFile(landuse_file.read())
        )
        try:
            # 转换为绝对路径
            abs_file_path = default_storage.path(file_path)
            
            # 如果是矢量（.zip/.shp），先栅格化为整型GeoTIFF
            raster_input = abs_file_path
            lower = file_path.lower()
            if lower.endswith('.zip') or lower.endswith('.shp'):
                if GDAL_IMPORT_ERROR or rasterize_shapefile_to_tiff is None:
                    return Response({
                        'error': f'Shapefile栅格化需要 GDAL/osgeo。当前环境未安装: {GDAL_IMPORT_ERROR}'
                    }, status=503)
                attr = request.data.get('landuse_attr') or 'class'
                try_fields = [attr, 'landuse', 'code', 'class_id']
                tmp_tif = os.path.splitext(abs_file_path)[0] + '.tif'
                last_err = None
                for field in try_fields:
                    try:
                        rasterize_shapefile_to_tiff(abs_file_path, tmp_tif, attribute_field=field)
                        raster_input = tmp_tif
                        break
                    except Exception as e:
                        last_err = e
                        continue
                else:
                    raise last_err or ValueError('栅格化失败，未找到有效属性字段')

            # 创建土地利用分析器
            analyzer_cls = LandUseAnalyzer if LandUseAnalyzer is not None else RasterioLandUseAnalyzer
            analyzer = analyzer_cls(raster_input)
            
            # 加载土地利用数据
            if not analyzer.load_landuse_data():
                return Response({
                    'error': '土地利用数据加载失败'
                }, status=400)
            
            # 计算各项生态环境胁迫指数
            results = {}
            
            # 1. 计算土壤侵蚀指数
            soil_erosion_result = analyzer.calculate_soil_erosion_index()
            if soil_erosion_result:
                results['soil_erosion'] = soil_erosion_result
            else:
                results['soil_erosion'] = {'error': '土壤侵蚀指数计算失败'}
            
            # 2. 计算未利用地面积比例
            unused_land_result = analyzer.calculate_unused_land_ratio()
            if unused_land_result:
                results['unused_land'] = unused_land_result
            else:
                results['unused_land'] = {'error': '未利用地面积比例计算失败'}
            
            # 3. 计算耕地建设用地面积比例
            cultivated_construction_result = analyzer.calculate_development_ratio()
            if cultivated_construction_result:
                results['cultivated_construction'] = cultivated_construction_result
            else:
                results['cultivated_construction'] = {'error': '耕地建设用地面积比例计算失败'}
            
            # 4. 计算土地退化指数
            land_degradation_result = analyzer.calculate_land_degradation_index()
            if land_degradation_result:
                results['land_degradation'] = land_degradation_result
            else:
                results['land_degradation'] = {'error': '土地退化指数计算失败'}

            visualization = _landuse_visualization_payload(request, analyzer, landuse_file.name)
            analyzer.close()
            
            # 清理临时文件
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:

                    os.remove(abs_file_path)

                except PermissionError:

                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:

                    os.remove(tif_candidate)

                except PermissionError:

                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
            
            return Response({
                'message': '生态环境胁迫指数计算完成',
                'results': results,
                'visualization': visualization,
                'summary': {
                    'soil_erosion_index': results.get('soil_erosion', {}).get('soil_erosion_index', 0),
                    'unused_land_proportion': results.get('unused_land', {}).get('unused_land_ratio', 0),
                    'cultivated_construction_proportion': results.get('cultivated_construction', {}).get('development_ratio', 0),
                    'land_degradation_index': results.get('land_degradation', {}).get('land_degradation_index', 0)
                }
            })
            
        except Exception as e:
            # 清理临时文件
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:

                    os.remove(abs_file_path)

                except PermissionError:

                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:

                    os.remove(tif_candidate)

                except PermissionError:

                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
            raise e
            
    except Exception as e:
        # 关闭分析器资源
        if 'analyzer' in locals():
            analyzer.close()
        
        # 清理临时文件
        try:
            abs_file_path = default_storage.path(file_path)
            if os.path.exists(abs_file_path):
                try:
                    os.remove(abs_file_path)
                except PermissionError:
                    logger.warning(f"无法删除文件 {abs_file_path}，可能仍被占用")
            tif_candidate = os.path.splitext(abs_file_path)[0] + '.tif'
            if os.path.exists(tif_candidate):
                try:
                    os.remove(tif_candidate)
                except PermissionError:
                    logger.warning(f"无法删除文件 {tif_candidate}，可能仍被占用")
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件时出错: {cleanup_error}")
        
        logger.error(f"计算生态环境胁迫指数失败: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'计算失败: {str(e)}',
            'traceback': traceback.format_exc()
        }, status=500)


# 气候监测相关视图
class ClimateDataFileViewSet(viewsets.ModelViewSet):
    """气候数据文件视图集"""
    queryset = ClimateDataFile.objects.all()
    serializer_class = ClimateDataFileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        """根据操作选择序列化器"""
        if self.action == 'create':
            return ClimateDataFileUploadSerializer
        return ClimateDataFileSerializer
    
    def perform_create(self, serializer):
        """创建时设置上传用户"""
        if self.request.user.is_authenticated:
            serializer.save(uploaded_by=self.request.user)
        else:
            serializer.save(uploaded_by=None)
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """开始气候数据分析"""
        try:
            from .climate_analysis import analyze_climate_data
            from .tasks import analyze_climate_data_task
            
            data_file = self.get_object()
            
            # 验证文件状态
            if data_file.status != 'uploaded':
                return Response({
                    'error': f'文件状态不正确，当前状态: {data_file.get_status_display()}'
                }, status=400)
            
            # 获取分析类型
            analysis_type = request.data.get('analysis_type', 'comprehensive')
            
            # 更新文件状态
            data_file.status = 'processing'
            data_file.save()
            
            # 创建处理任务
            task = ProcessingTask.objects.create(
                task_type=f'气候数据分析 - {analysis_type}',
                status='pending',
                created_by=request.user if request.user.is_authenticated else None
            )
            
            # 启动异步分析任务
            # 确保参数类型正确
            file_id_str = str(data_file.id)
            task_id_str = str(task.id)
            analyze_climate_data_task.delay(file_id_str, task_id_str, analysis_type)
            
            return Response({
                'success': True,
                'message': '分析任务已启动',
                'task_id': task.id,
                'file_id': data_file.id
            })
            
        except Exception as e:
            logger.error(f"启动气候数据分析失败: {str(e)}")
            return Response({
                'error': f'启动分析失败: {str(e)}'
            }, status=500)
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """获取分析结果"""
        try:
            data_file = self.get_object()
            results = ClimateAnalysisResult.objects.filter(data_file=data_file).order_by('-created_at')
            
            if not results.exists():
                return Response({
                    'error': '暂无分析结果'
                }, status=404)
            
            latest_result = results.first()
            serializer = ClimateAnalysisResultSerializer(latest_result)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"获取分析结果失败: {str(e)}")
            return Response({
                'error': f'获取结果失败: {str(e)}'
            }, status=500)


def validate_climate_file(file_obj):
    """验证气候数据文件"""
    errors = []
    
    # 1. 检查文件是否存在
    if not file_obj:
        errors.append('文件对象不存在')
        return errors
    
    # 2. 检查文件大小（栅格数据可能较大，后端会落盘并分块统计）
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024 * 1024)
    if file_obj.size > max_size:
        errors.append(f'文件大小不能超过{max_size / (1024*1024*1024):.1f}GB，当前大小: {file_obj.size / (1024*1024):.2f}MB')
    
    # 3. 检查文件是否为空
    if file_obj.size == 0:
        errors.append('文件不能为空')
    
    # 4. 检查文件类型
    file_name = file_obj.name.lower()
    if not file_name.endswith(('.csv', '.xlsx', '.xls', '.tif', '.tiff', '.zip')):
        errors.append('只支持CSV、Excel、GeoTIFF或ADF ZIP文件格式(.csv, .xlsx, .xls, .tif, .tiff, .zip)')
    
    # 5. 检查文件名
    if not file_name or file_name.strip() == '':
        errors.append('文件名不能为空')
    
    # 6. 检查文件名长度
    if len(file_name) > 255:
        errors.append('文件名过长，不能超过255个字符')
    
    return errors

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def upload_climate_data(request):
    """上传气候数据文件"""
    try:
        # 验证请求数据
        if not request.data:
            return Response({
                'error': '请求数据为空'
            }, status=400)
        
        # 验证文件是否存在
        if 'file' not in request.FILES:
            return Response({
                'error': '没有找到文件'
            }, status=400)
        
        file_obj = request.FILES['file']
        
        # 验证文件
        file_errors = validate_climate_file(file_obj)
        if file_errors:
            return Response({
                'error': '文件验证失败',
                'details': file_errors
            }, status=400)
        
        # 验证请求数据
        required_fields = ['name']
        for field in required_fields:
            if field not in request.data or not request.data[field]:
                return Response({
                    'error': f'缺少必需字段: {field}'
                }, status=400)
        
        # 验证字段长度
        if len(request.data['name']) > 255:
            return Response({
                'error': '名称过长，不能超过255个字符'
            }, status=400)
        
        # 序列化数据
        serializer = ClimateDataFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            # 确定文件类型
            file_name = file_obj.name.lower()
            if file_name.endswith('.csv'):
                file_type = 'csv'
            elif file_name.endswith(('.xlsx', '.xls')):
                file_type = 'xlsx'
            elif file_name.endswith(('.tif', '.tiff')):
                file_type = 'tif'
            elif file_name.endswith('.zip'):
                file_type = 'zip'
            else:
                return Response({
                    'error': '不支持的文件格式'
                }, status=400)
            
            # 创建文件记录
            try:
                data_file = ClimateDataFile.objects.create(
                    name=serializer.validated_data['name'],
                    file=file_obj,
                    file_type=file_type,
                    description=serializer.validated_data.get('description', ''),
                    uploaded_by=request.user if request.user.is_authenticated else None
                )
                
                logger.info(f"气候数据文件上传成功: {data_file.id} - {data_file.name}")
                
                return Response({
                    'success': True,
                    'file_id': data_file.id,
                    'message': '文件上传成功'
                })
            except Exception as e:
                logger.error(f"创建文件记录失败: {str(e)}")
                return Response({
                    'error': '文件保存失败',
                    'details': str(e)
                }, status=500)
        else:
            logger.warning(f"文件上传数据验证失败: {serializer.errors}")
            return Response({
                'error': '数据验证失败',
                'details': serializer.errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"文件上传异常: {str(e)}")
        return Response({
            'error': '文件上传失败',
            'details': str(e)
        }, status=500)


def validate_analysis_request(data):
    """验证分析请求数据"""
    errors = []
    
    # 1. 检查必需字段
    required_fields = ['file_id', 'analysis_type']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'缺少必需字段: {field}')
    
    # 2. 验证file_id格式
    if 'file_id' in data and data['file_id']:
        try:
            import uuid
            uuid.UUID(data['file_id'])
        except (ValueError, TypeError):
            errors.append('file_id格式无效，应为UUID格式')
    
    # 3. 验证analysis_type
    if 'analysis_type' in data and data['analysis_type']:
        valid_types = ['comprehensive', 'temperature', 'precipitation', 'humidity', 'wind']
        if data['analysis_type'] not in valid_types:
            errors.append(f'analysis_type无效，支持的类型: {", ".join(valid_types)}')
    
    return errors

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def analyze_climate_data_api(request):
    """气候数据分析API"""
    try:
        # 验证请求数据
        if not request.data:
            return Response({
                'error': '请求数据为空'
            }, status=400)
        
        # 验证分析请求
        validation_errors = validate_analysis_request(request.data)
        if validation_errors:
            return Response({
                'error': '请求数据验证失败',
                'details': validation_errors
            }, status=400)
        
        serializer = ClimateAnalysisRequestSerializer(data=request.data)
        if serializer.is_valid():
            file_id = serializer.validated_data['file_id']
            analysis_type = serializer.validated_data['analysis_type']
            
            # 验证文件是否存在
            try:
                data_file = ClimateDataFile.objects.get(id=file_id)
            except ClimateDataFile.DoesNotExist:
                logger.warning(f"分析请求失败: 文件不存在 - {file_id}")
                return Response({
                    'error': '文件不存在'
                }, status=404)
            except Exception as e:
                logger.error(f"查询文件失败: {str(e)}")
                return Response({
                    'error': '文件查询失败'
                }, status=500)
            
            # 检查文件状态
            if data_file.status != 'uploaded':
                logger.warning(f"分析请求失败: 文件状态不正确 - {data_file.id}, 状态: {data_file.status}")
                return Response({
                    'error': f'文件状态不正确，当前状态: {data_file.get_status_display()}'
                }, status=400)
            
            # 检查文件是否真的存在
            if not data_file.file or not data_file.file.name:
                logger.error(f"文件记录存在但文件不存在: {data_file.id}")
                return Response({
                    'error': '文件数据损坏，请重新上传'
                }, status=400)
            
            # 更新文件状态
            try:
                data_file.status = 'processing'
                data_file.save()
                logger.info(f"文件状态更新为processing: {data_file.id}")
            except Exception as e:
                logger.error(f"更新文件状态失败: {str(e)}")
                return Response({
                    'error': '更新文件状态失败'
                }, status=500)
            
            # 创建处理任务
            try:
                task = ProcessingTask.objects.create(
                    task_type=f'气候数据分析 - {analysis_type}',
                    status='pending',
                    created_by=request.user if request.user.is_authenticated else None
                )
                logger.info(f"创建分析任务: {task.id} - {task.task_type}")
            except Exception as e:
                logger.error(f"创建处理任务失败: {str(e)}")
                return Response({
                    'error': '创建分析任务失败'
                }, status=500)
            
            # 启动分析任务
            from .tasks import analyze_climate_data_task
            from django.conf import settings
            
            # 在开发环境中直接执行任务，生产环境中使用异步
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
                # 开发环境：直接执行
                try:
                    # 确保参数类型正确
                    file_id_str = str(file_id)
                    task_id_str = str(task.id)
                    result = analyze_climate_data_task(file_id_str, task_id_str, analysis_type)
                    logger.info(f"任务直接执行完成: {result}")
                except Exception as e:
                    logger.error(f"任务直接执行失败: {str(e)}")
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.save()
            else:
                # 生产环境：异步执行
                # 确保参数类型正确
                file_id_str = str(file_id)
                task_id_str = str(task.id)
                analyze_climate_data_task.delay(file_id_str, task_id_str, analysis_type)
            
            return Response({
                'success': True,
                'task_id': task.id,
                'message': '分析任务已启动'
            })
        else:
            return Response({
                'error': '数据验证失败',
                'details': serializer.errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"气候数据分析API失败: {str(e)}")
        return Response({
            'error': f'分析失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_climate_analysis_results(request, task_id):
    """获取气候分析结果"""
    try:
        task = ProcessingTask.objects.get(id=task_id)
        
        if task.status != 'completed':
            return Response({
                'success': False,
                'status': task.status,
                'message': '分析尚未完成'
            })
        
        # 查找对应的分析结果
        try:
            # 根据任务类型查找对应的分析结果
            if '气候数据分析' in task.task_type:
                # 查找气候分析结果
                from .models import ClimateAnalysisResult
                
                # 查找最近的气候分析结果
                results = ClimateAnalysisResult.objects.all().order_by('-created_at')[:1]
                
                if results.exists():
                    latest_result = results.first()
                    serializer = ClimateAnalysisResultSerializer(latest_result)
                    
                    return Response({
                        'success': True,
                        'status': task.status,
                        'task_id': task.id,
                        'message': '分析完成',
                        'data': serializer.data
                    })
                else:
                    return Response({
                        'success': False,
                        'status': task.status,
                        'message': '未找到分析结果数据'
                    })
            else:
                # 其他类型的任务
                return Response({
                    'success': True,
                    'status': task.status,
                    'task_id': task.id,
                    'message': '分析完成'
                })
                
        except Exception as e:
            logger.error(f"查找分析结果失败: {str(e)}")
            return Response({
                'success': False,
                'status': task.status,
                'message': f'查找分析结果失败: {str(e)}'
            })
        
    except ProcessingTask.DoesNotExist:
        return Response({
            'error': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取气候分析结果失败: {str(e)}")
        return Response({
            'error': f'获取结果失败: {str(e)}'
        }, status=500)


# 业务图层上传/发布
class BusinessLayerViewSet(viewsets.ModelViewSet):
    """业务图层：上传用户成果数据并发布为GeoServer WMS/WFS/WCS服务"""
    queryset = BusinessLayer.objects.all()
    serializer_class = BusinessLayerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        read_actions = {'list', 'retrieve', 'logs'}
        if self.action in read_actions:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            if self.request.data.get('service_url'):
                return BusinessLayerServiceSerializer
            return BusinessLayerUploadSerializer
        return BusinessLayerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        layer = serializer.save(
            uploaded_by=request.user if request.user.is_authenticated else None,
            status='uploaded'
        )

        try:
            if layer.service_url:
                self._register_external_service_layer(layer)
            else:
                self._publish_layer(layer)
            _log_business_layer_action(
                layer,
                'upload',
                'success' if layer.status == 'published' else 'info',
                '业务图层已创建',
                operator=request.user,
                details={'source_format': layer.source_format, 'status': layer.status}
            )
        except Exception as exc:
            logger.error(f"业务图层发布失败: {exc}")
            import traceback
            logger.error(traceback.format_exc())
            layer.status = 'failed'
            layer.error_message = str(exc)
            layer.save(update_fields=['status', 'error_message', 'updated_at'])
            _log_business_layer_action(layer, 'upload', 'failed', str(exc), operator=request.user)

        layer.refresh_from_db()
        response_status = status.HTTP_201_CREATED if layer.status == 'published' else status.HTTP_202_ACCEPTED
        return Response(BusinessLayerSerializer(layer, context={'request': request}).data, status=response_status)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """重新发布已上传的业务图层"""
        layer = self.get_object()
        try:
            if layer.service_url:
                self._register_external_service_layer(layer)
            else:
                self._publish_layer(layer)
            _log_business_layer_action(layer, 'publish', 'success', '业务图层发布成功', operator=request.user)
        except Exception as exc:
            layer.status = 'failed'
            layer.error_message = str(exc)
            layer.save(update_fields=['status', 'error_message', 'updated_at'])
            _log_business_layer_action(layer, 'publish', 'failed', str(exc), operator=request.user)
            return Response(BusinessLayerSerializer(layer, context={'request': request}).data, status=500)

        layer.refresh_from_db()
        return Response(BusinessLayerSerializer(layer, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """撤销GeoServer发布，但保留用户上传的源文件和系统记录"""
        layer = self.get_object()
        try:
            self._unpublish_layer(layer)
            _log_business_layer_action(layer, 'unpublish', 'success', '业务图层已撤销发布', operator=request.user)
        except Exception as exc:
            logger.error(f"业务图层撤销发布失败: {exc}")
            _log_business_layer_action(layer, 'unpublish', 'failed', str(exc), operator=request.user)
            return Response({'error': str(exc)}, status=500)

        layer.refresh_from_db()
        return Response(BusinessLayerSerializer(layer, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        """删除业务图层记录；如果已发布，先同步清理GeoServer服务"""
        layer = self.get_object()
        layer_name = layer.name
        if layer.status == 'published' or layer.geoserver_store_name:
            self._unpublish_layer(layer, raise_on_error=False)
        _log_business_layer_action(layer, 'delete', 'success', f'业务图层 {layer_name} 已删除', operator=request.user)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        layer = self.get_object()
        queryset = layer.audit_logs.all()
        return Response(BusinessLayerAuditLogSerializer(queryset, many=True).data)

    @action(detail=True, methods=['post'])
    def style(self, request, pk=None):
        layer = self.get_object()
        serializer = BusinessLayerStyleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        style_config = serializer.validated_data

        try:
            self._apply_business_layer_style(layer, style_config, operator=request.user)
        except Exception as exc:
            logger.error(f"业务图层样式更新失败: {exc}")
            _log_business_layer_action(layer, 'style_update', 'failed', str(exc), operator=request.user)
            return Response({'error': str(exc)}, status=400)

        layer.refresh_from_db()
        return Response(BusinessLayerSerializer(layer, context={'request': request}).data)

    def _publish_layer(self, layer):
        from .geoserver_config import get_geoserver_manager

        layer.status = 'publishing'
        layer.error_message = ''
        layer.save(update_fields=['status', 'error_message', 'updated_at'])

        if not layer.file:
            raise ValueError('当前业务图层没有源文件，无法发布到 GeoServer')

        geoserver = get_geoserver_manager()
        geoserver.create_workspace()

        source_path = layer.file.path
        layer_name = _safe_layer_name(layer.name or os.path.splitext(os.path.basename(source_path))[0])

        if layer.layer_type == 'vector':
            extract_dir = os.path.join(settings.MEDIA_ROOT, 'business_layers', str(layer.id), 'vector')
            if layer.source_format == 'kml':
                shp_path = _convert_kml_to_shapefile(source_path, extract_dir, layer_name)
                charset = 'UTF-8'
            else:
                is_valid_zip, zip_message = validate_shapefile_zip(source_path)
                if not is_valid_zip:
                    raise ValueError(zip_message)

                shp_path = _extract_shapefile_zip(source_path, extract_dir)
                cpg_path = os.path.splitext(shp_path)[0] + '.cpg'
                charset = 'GBK'
                if os.path.exists(cpg_path):
                    with open(cpg_path, 'r', encoding='utf-8', errors='ignore') as cpg_file:
                        charset = cpg_file.read().strip() or charset

            published = geoserver.publish_shapefile(layer_name, shp_path, charset=charset)
            store_name = f'{layer_name}_store'
            metadata = {
                **(layer.metadata or {}),
                'source_shp_path': shp_path,
                'charset': charset,
                'source_origin': 'upload',
                **_vector_layer_metadata(shp_path),
            }
        else:
            store_name = f'{layer_name}_store'
            published = geoserver.publish_raster(store_name, layer_name, source_path)
            metadata = {
                **(layer.metadata or {}),
                'source_raster_path': source_path,
                'source_origin': 'upload',
                **_raster_layer_metadata(source_path),
            }

        urls = _build_ogc_urls(geoserver, layer_name, layer.layer_type)
        health = _check_layer_service_availability(layer=type('LayerProbe', (), {
            'layer_type': layer.layer_type,
            'wms_url': urls['wms_url'],
            'wfs_url': urls['wfs_url'],
            'wcs_url': urls['wcs_url'],
            'service_type_name': None,
            'geoserver_layer_name': layer_name,
            'geoserver_workspace': geoserver.workspace,
            'service_srs': metadata.get('crs'),
            'metadata': metadata,
        })())
        layer.geoserver_workspace = geoserver.workspace
        layer.geoserver_store_name = store_name
        layer.geoserver_layer_name = layer_name
        layer.wms_url = urls['wms_url']
        layer.wfs_url = urls['wfs_url']
        layer.wcs_url = urls['wcs_url']
        layer.metadata = metadata
        layer.status = 'published' if published else 'failed'
        layer.error_message = '' if published else 'GeoServer发布失败，请检查GeoServer服务、文件路径和日志'
        layer.published_at = timezone.now() if published else None
        layer.service_srs = metadata.get('crs')
        layer.service_health_status = health['service_health_status'] if published else 'unhealthy'
        layer.service_health_message = health['service_health_message'] if published else layer.error_message
        layer.service_checked_at = health['service_checked_at'] if published else timezone.now()
        layer.save()

        if published:
            self._apply_business_layer_style(layer)

        if not published:
            raise RuntimeError(layer.error_message)

    def _register_external_service_layer(self, layer):
        metadata = dict(layer.metadata or {})
        metadata['is_external_service'] = True
        metadata['service_registered_at'] = timezone.now().isoformat()
        metadata['source_origin'] = 'external_service'

        service_url = (layer.service_url or '').strip()
        service_type_name = (layer.service_type_name or '').strip()

        if layer.source_format == 'wms':
            layer.wms_url = service_url
            layer.wfs_url = None
            layer.wcs_url = None
        elif layer.source_format == 'wfs':
            layer.wms_url = None
            layer.wfs_url = service_url
            layer.wcs_url = None
        elif layer.source_format == 'wcs':
            layer.wms_url = None
            layer.wfs_url = None
            layer.wcs_url = service_url

        layer.geoserver_workspace = None
        layer.geoserver_store_name = None
        layer.geoserver_layer_name = service_type_name or layer.name
        layer.metadata = metadata
        layer.status = 'published'
        layer.error_message = ''
        layer.published_at = timezone.now()
        health = _check_layer_service_availability(layer)
        layer.service_health_status = health['service_health_status']
        layer.service_health_message = health['service_health_message']
        layer.service_checked_at = health['service_checked_at']
        layer.save()
        if layer.source_format == 'wms' and layer.style_config:
            _log_business_layer_action(layer, 'style_update', 'info', '外部服务已记录样式配置，需由外部服务端实际生效', operator=None)

    def _unpublish_layer(self, layer, raise_on_error=True):
        from .geoserver_config import get_geoserver_manager

        metadata = dict(layer.metadata or {})
        if metadata.get('is_external_service'):
            metadata['last_unpublished_at'] = timezone.now().isoformat()
            layer.status = 'uploaded'
            layer.error_message = ''
            layer.wms_url = None
            layer.wfs_url = None
            layer.wcs_url = None
            layer.published_at = None
            layer.service_health_status = 'unknown'
            layer.service_health_message = '服务已撤销发布'
            layer.service_checked_at = timezone.now()
            layer.metadata = metadata
            layer.save(update_fields=[
                'status', 'error_message', 'wms_url', 'wfs_url', 'wcs_url',
                'published_at', 'service_health_status', 'service_health_message',
                'service_checked_at', 'metadata', 'updated_at'
            ])
            return

        geoserver = get_geoserver_manager()
        store_name = layer.geoserver_store_name
        if not store_name and layer.geoserver_layer_name:
            store_name = f'{layer.geoserver_layer_name}_store'

        success = True
        if store_name:
            if layer.layer_type == 'vector':
                success = geoserver.delete_datastore(store_name, recurse=True)
            else:
                success = geoserver.delete_coveragestore(store_name, recurse=True)

        if not success and raise_on_error:
            raise RuntimeError('GeoServer服务清理失败，请检查GeoServer是否启动或手动删除对应存储')

        metadata = dict(layer.metadata or {})
        metadata['last_unpublished_at'] = timezone.now().isoformat()
        layer.status = 'uploaded'
        layer.error_message = '' if success else 'GeoServer服务清理失败，数据库记录已保留'
        layer.geoserver_workspace = None
        layer.geoserver_store_name = None
        layer.geoserver_layer_name = None
        layer.wms_url = None
        layer.wfs_url = None
        layer.wcs_url = None
        layer.published_at = None
        layer.service_health_status = 'unknown'
        layer.service_health_message = '服务已撤销发布'
        layer.service_checked_at = timezone.now()
        layer.metadata = metadata
        layer.save()

    def _apply_business_layer_style(self, layer, style_config=None, operator=None):
        from .geoserver_config import get_geoserver_manager

        next_style_config = dict(layer.style_config or {})
        if style_config:
            next_style_config.update(style_config)

        if layer.metadata.get('is_external_service'):
            layer.style_name = next_style_config.get('style_name') or layer.style_name
            layer.style_config = next_style_config
            if style_config and 'sld_content' in style_config:
                layer.sld_content = style_config.get('sld_content') or None
            layer.save(update_fields=['style_name', 'style_config', 'sld_content', 'updated_at'])
            _log_business_layer_action(
                layer,
                'style_update',
                'info',
                '外部服务图层仅记录样式配置，未直接改写远程服务样式',
                operator=operator,
                details={'style_name': layer.style_name, 'style_config': layer.style_config}
            )
            return

        if not layer.geoserver_layer_name:
            raise ValueError('当前图层尚未发布到 GeoServer，不能应用样式')

        geoserver = get_geoserver_manager()
        metadata = dict(layer.metadata or {})
        if layer.layer_type == 'vector':
            vector_meta = metadata.get('style_vector_meta') or {}
            if not vector_meta:
                source_path = metadata.get('source_shp_path')
                geometry_type = 'polygon'
                classification_field = next_style_config.get('classification_field')
                min_value = None
                max_value = None
                if source_path:
                    try:
                        from osgeo import ogr
                        datasource = ogr.Open(source_path)
                        if datasource:
                            source_layer = datasource.GetLayer(0)
                            geom_name = source_layer.GetGeomType()
                            if geom_name in [1, 4]:
                                geometry_type = 'point'
                            elif geom_name in [2, 5]:
                                geometry_type = 'line'
                            if classification_field:
                                values = []
                                for feature in source_layer:
                                    value = feature.GetField(classification_field)
                                    if value is not None:
                                        try:
                                            values.append(float(value))
                                        except (TypeError, ValueError):
                                            pass
                                if values:
                                    min_value = min(values)
                                    max_value = max(values)
                            datasource = None
                    except Exception as exc:
                        logger.warning(f'读取矢量样式元数据失败: {exc}')
                vector_meta = {
                    'geometry_type': geometry_type,
                    'min_value': min_value,
                    'max_value': max_value,
                }
            next_style_config.setdefault('geometry_type', vector_meta.get('geometry_type') or 'polygon')
            if vector_meta.get('min_value') is not None:
                next_style_config['min_value'] = vector_meta['min_value']
            if vector_meta.get('max_value') is not None:
                next_style_config['max_value'] = vector_meta['max_value']
            generated_sld = next_style_config.get('sld_content') or _vector_style_sld(layer.geoserver_layer_name, next_style_config)
        else:
            raster_meta = metadata.get('style_raster_meta') or {}
            if not raster_meta:
                source_path = metadata.get('source_raster_path')
                if source_path and os.path.exists(source_path):
                    try:
                        with rasterio.open(source_path) as dataset:
                            data = dataset.read(1, masked=True)
                            valid_data = data.compressed() if hasattr(data, 'compressed') else data.flatten()
                            if valid_data.size:
                                raster_meta = {
                                    'min_value': float(np.min(valid_data)),
                                    'max_value': float(np.max(valid_data)),
                                    'nodata': dataset.nodata,
                                }
                    except Exception as exc:
                        logger.warning(f'读取栅格样式元数据失败: {exc}')
            next_style_config.setdefault('min_value', raster_meta.get('min_value', 0.0))
            next_style_config.setdefault('max_value', raster_meta.get('max_value', 100.0))
            next_style_config.setdefault('nodata', raster_meta.get('nodata'))
            generated_sld = next_style_config.get('sld_content') or _raster_style_sld(layer.geoserver_layer_name, next_style_config)

        style_name = next_style_config.get('style_name') or layer.style_name or f'{layer.geoserver_layer_name}_style'
        created = geoserver.create_style(style_name, generated_sld)
        if not created:
            raise RuntimeError('GeoServer 样式创建或更新失败')
        if not geoserver.apply_style_to_layer(layer.geoserver_layer_name, style_name):
            raise RuntimeError('GeoServer 样式应用失败')

        layer.style_name = style_name
        layer.style_config = {key: value for key, value in next_style_config.items() if key != 'sld_content'}
        layer.sld_content = generated_sld
        layer.metadata = metadata
        layer.save(update_fields=['style_name', 'style_config', 'sld_content', 'metadata', 'updated_at'])
        _log_business_layer_action(
            layer,
            'style_update',
            'success',
            '业务图层样式已更新',
            operator=operator,
            details={'style_name': style_name, 'style_config': layer.style_config}
        )


# 叠加分析相关视图集

class EcologicalIndexFileViewSet(viewsets.ModelViewSet):
    """生态指数文件视图集"""
    queryset = EcologicalIndexFile.objects.all()
    serializer_class = EcologicalIndexFileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return EcologicalIndexFileUploadSerializer
        return EcologicalIndexFileSerializer

    def perform_create(self, serializer):
        """处理文件上传"""
        instance = serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)

        # 处理上传的JSON文件
        try:
            file_content = instance.file.read().decode('utf-8')
            indices_data = json.loads(file_content)

            # 保存解析后的数据
            instance.indices_data = indices_data
            instance.timestamp = timezone.now()
            instance.status = 'completed'
            instance.processed_at = timezone.now()
            instance.save()

        except Exception as e:
            instance.status = 'failed'
            instance.error_message = f"文件解析失败: {str(e)}"
            instance.save()
            logger.error(f"生态指数文件解析失败: {str(e)}")


class EcologicalProjectFileViewSet(viewsets.ModelViewSet):
    """生态修复工程文件视图集"""
    queryset = EcologicalProjectFile.objects.all()
    serializer_class = EcologicalProjectFileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return EcologicalProjectFileUploadSerializer
        return EcologicalProjectFileSerializer

    def perform_create(self, serializer):
        """处理文件上传"""
        instance = serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)

        # 处理上传的GeoJSON文件
        try:
            file_content = instance.file.read().decode('utf-8')
            geojson_data = json.loads(file_content)

            # 验证GeoJSON格式
            if geojson_data.get('type') != 'FeatureCollection':
                raise ValueError("文件必须是有效的GeoJSON FeatureCollection格式")

            # 保存解析后的数据
            instance.geojson_data = geojson_data
            instance.status = 'completed'
            instance.processed_at = timezone.now()
            instance.save()

        except Exception as e:
            instance.status = 'failed'
            instance.error_message = f"文件解析失败: {str(e)}"
            instance.save()
            logger.error(f"生态修复工程文件解析失败: {str(e)}")


class OverlayAnalysisTaskViewSet(viewsets.ModelViewSet):
    """叠加分析任务视图集"""
    queryset = OverlayAnalysisTask.objects.all()
    serializer_class = OverlayAnalysisTaskSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # 支持文件上传

    def get_serializer_class(self):
        if self.action == 'create':
            return OverlayAnalysisTaskCreateSerializer
        return OverlayAnalysisTaskSerializer

    def perform_create(self, serializer):
        """创建叠加分析任务"""
        instance = serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

        # 异步执行分析（这里简化为同步执行）
        try:
            from .overlay_analysis import perform_overlay_analysis
            perform_overlay_analysis(str(instance.id))
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"启动叠加分析失败: {str(e)}")
            logger.error(f"错误堆栈:\n{error_trace}")
            instance.status = 'failed'
            instance.error_message = str(e)
            instance.save()
            # 不要重新抛出异常，让DRF正常返回创建成功的响应
            # 前端可以通过轮询任务状态来获取失败信息

    @action(detail=False, methods=['delete'], url_path='delete-uploaded-layer')
    def delete_uploaded_layer(self, request):
        """删除叠加分析中已上传并发布的固定业务图层"""
        layer_type = request.query_params.get('data_type') or request.data.get('data_type')
        layer_configs = {
            'ecology': {
                'label': '生态指数栅格',
                'store': 'ecology_raster',
                'kind': 'raster',
                'paths': [
                    os.path.join(settings.MEDIA_ROOT, 'ecological_projects', 'ecology_raster.tif'),
                ],
            },
            'economy': {
                'label': '经济数据矢量',
                'store': 'economy_vector_store',
                'kind': 'vector',
                'paths': [
                    os.path.join(settings.MEDIA_ROOT, 'ecological_projects', 'economy_vector'),
                ],
            },
            'engineering': {
                'label': '工程项目矢量',
                'store': 'engineering_vector_store',
                'kind': 'vector',
                'paths': [
                    os.path.join(settings.MEDIA_ROOT, 'ecological_projects', 'engineering_vector'),
                ],
            },
        }

        if layer_type not in layer_configs:
            return Response({
                'success': False,
                'message': '不支持的数据类型'
            }, status=400)

        config = layer_configs[layer_type]
        geoserver_success = True
        try:
            from .geoserver_config import geoserver_manager
            if config['kind'] == 'raster':
                geoserver_success = geoserver_manager.delete_coveragestore(config['store'], recurse=True)
            else:
                geoserver_success = geoserver_manager.delete_datastore(config['store'], recurse=True)
        except Exception as exc:
            geoserver_success = False
            logger.warning(f"删除{config['label']}GeoServer服务失败: {exc}")

        removed_paths = []
        for path in config['paths']:
            try:
                if os.path.isdir(path):
                    remove_tree(path)
                    removed_paths.append(path)
                elif os.path.exists(path):
                    os.remove(path)
                    removed_paths.append(path)
            except Exception as exc:
                logger.warning(f"删除本地文件失败 {path}: {exc}")

        return Response({
            'success': geoserver_success,
            'message': f"{config['label']}已删除" if geoserver_success else f"{config['label']}本地记录已清理，但GeoServer服务删除可能未完成",
            'data_type': layer_type,
            'removed_paths': removed_paths,
        })

    @action(detail=True, methods=['post'])
    def restart_analysis(self, request, pk=None):
        """重新启动分析"""
        task = self.get_object()

        if task.status in ['processing']:
            return Response({
                'error': '任务正在进行中，无法重新启动'
            }, status=400)

        try:
            # 重置任务状态
            task.status = 'pending'
            task.progress = 0
            task.current_step = None
            task.error_message = None
            task.analysis_results = {}
            task.overall_risk_level = None
            task.started_at = None
            task.completed_at = None
            task.save()

            # 重新执行分析
            from .overlay_analysis import perform_overlay_analysis
            perform_overlay_analysis(str(task.id))

            return Response({
                'message': '分析已重新启动',
                'task_id': task.id
            })

        except Exception as e:
            logger.error(f"重新启动分析失败: {str(e)}")
            return Response({
                'error': f'重新启动失败: {str(e)}'
            }, status=500)

    @action(detail=False, methods=['get'])
    def risk_statistics(self, request):
        """获取风险统计信息"""
        try:
            # 统计各风险等级的任务数量
            risk_stats = {}
            for choice in OverlayAnalysisTask.RISK_LEVEL_CHOICES:
                level = choice[0]
                count = OverlayAnalysisTask.objects.filter(
                    overall_risk_level=level,
                    status='completed'
                ).count()
                risk_stats[level] = count

            # 统计任务状态
            status_stats = {}
            for choice in OverlayAnalysisTask.STATUS_CHOICES:
                status = choice[0]
                count = OverlayAnalysisTask.objects.filter(status=status).count()
                status_stats[status] = count

            return Response({
                'risk_distribution': risk_stats,
                'status_distribution': status_stats,
                'total_tasks': OverlayAnalysisTask.objects.count(),
                'completed_tasks': OverlayAnalysisTask.objects.filter(status='completed').count()
            })

        except Exception as e:
            logger.error(f"获取风险统计失败: {str(e)}")
            return Response({
                'error': f'获取统计信息失败: {str(e)}'
            }, status=500)

    @action(detail=True, methods=['post'])
    def republish_raster_layers(self, request, pk=None):
        """重新发布栅格图层到GeoServer"""
        task = self.get_object()
        
        try:
            from .geoserver_config import get_geoserver_manager
            
            geoserver = get_geoserver_manager()
            
            # 确保工作空间存在
            geoserver.create_workspace()
            
            # 清理旧的CoverageStore（如果需要）
            coverage_store_name = f"overlay_{task.id}"
            geoserver.delete_coveragestore(coverage_store_name, recurse=True)
            
            # 获取栅格文件
            published_layers = {}
            raster_metadata = task.raster_layers_metadata.copy() if task.raster_layers_metadata else {}
            error_messages = []  # 收集错误信息
            
            # 发布风险栅格
            if task.risk_raster_file:
                risk_file_path = task.risk_raster_file.path
                if os.path.exists(risk_file_path):
                    layer_name = f"risk_layer_{task.id}"
                    logger.info(f"开始重新发布风险栅格图层: {layer_name}")
                    logger.info(f"栅格文件路径: {risk_file_path}")
                    
                    # 先删除可能存在的旧图层（如果名称不同）
                    try:
                        full_layer_name = f"{geoserver.workspace}:{layer_name}"
                        old_layer_check = geoserver.get_layer_info(full_layer_name)
                        if old_layer_check:
                            logger.info(f"发现旧图层 {layer_name}，尝试删除")
                            # 尝试通过GeoServer REST API删除图层
                            try:
                                delete_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                                import requests
                                response = requests.delete(delete_url, auth=geoserver.auth, timeout=30)
                                if response.status_code in [200, 204]:
                                    logger.info(f"旧图层 {layer_name} 删除成功")
                                else:
                                    logger.warning(f"删除旧图层返回状态码: {response.status_code}")
                            except Exception as del_error:
                                logger.warning(f"删除旧图层时出错: {del_error}")
                            time.sleep(1)
                    except Exception as e:
                        logger.warning(f"检查旧图层时出错（可能不存在）: {e}")
                    
                    publish_result = geoserver.publish_raster(coverage_store_name, layer_name, risk_file_path)
                    logger.info(f"publish_raster 返回结果: {publish_result}")
                    
                    if publish_result:
                        # 等待一下让GeoServer处理
                        time.sleep(3)  # 增加等待时间，确保重命名完成
                        
                        # 验证图层是否存在（先尝试期望的名称）
                        full_layer_name = f"{geoserver.workspace}:{layer_name}"
                        layer_check = geoserver.get_layer_info(full_layer_name)
                        logger.info(f"图层验证结果（期望名称 {layer_name}）: {layer_check is not None}")
                        
                        # 如果期望名称的图层不存在，尝试查找实际创建的图层名称（可能是CoverageStore名称）
                        actual_layer_name = layer_name
                        if not layer_check:
                            logger.info(f"⚠️ 期望图层名称 {layer_name} 不存在，尝试查找实际创建的图层...")
                            # 检查CoverageStore中的Coverage名称
                            try:
                                coverage_list = geoserver._make_request('GET', f'workspaces/{geoserver.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                                if coverage_list and 'coverages' in coverage_list:
                                    coverages = coverage_list['coverages'].get('coverage', [])
                                    if isinstance(coverages, list) and len(coverages) > 0:
                                        coverage_obj = coverages[0]
                                        if isinstance(coverage_obj, dict):
                                            actual_layer_name = coverage_obj.get('name', layer_name)
                                        else:
                                            actual_layer_name = coverage_store_name  # 使用CoverageStore名称
                                    elif isinstance(coverages, dict):
                                        actual_layer_name = coverages.get('name', layer_name)
                                    else:
                                        actual_layer_name = coverage_store_name  # 使用CoverageStore名称
                                    
                                    logger.info(f"找到实际图层名称: {actual_layer_name}")
                                    # 验证实际图层是否存在
                                    full_actual_name = f"{geoserver.workspace}:{actual_layer_name}"
                                    layer_check = geoserver.get_layer_info(full_actual_name)
                                    if layer_check:
                                        logger.info(f"✅ 找到实际创建的图层: {actual_layer_name}")
                                        layer_name = actual_layer_name  # 使用实际图层名称
                                    else:
                                        logger.warning(f"⚠️ 实际图层名称 {actual_layer_name} 也不存在，可能GeoServer尚未完全处理")
                            except Exception as e:
                                logger.warning(f"⚠️ 查找实际图层名称时出错: {e}")
                        
                        if layer_check:
                            # 为图层创建并应用默认样式
                            style_name = f"{layer_name}_style"
                            logger.info(f"为图层 {layer_name} 创建样式: {style_name}")
                            
                            # 从栅格文件读取统计信息，以创建合适的样式
                            # 快速模式：使用默认值域，避免长时间读取栅格数据
                            logger.info(f"快速模式：使用默认值域创建样式（避免长时间读取栅格数据）")
                            min_val, max_val = (0.0, 5.0)
                            
                            # 可选：尝试快速读取统计信息（不阻塞）
                            try:
                                import threading
                                result = [None]
                                def quick_get_stats():
                                    try:
                                        result[0] = geoserver._get_raster_statistics(risk_file_path)
                                    except:
                                        pass
                                
                                thread = threading.Thread(target=quick_get_stats)
                                thread.daemon = True
                                thread.start()
                                thread.join(timeout=3)  # 3秒超时
                                
                                if result[0] and not thread.is_alive():
                                    min_val, max_val = result[0]
                                    logger.info(f"✅ 快速获取到统计信息，更新值域: {min_val} - {max_val}")
                            except:
                                pass
                            
                            logger.info(f"使用栅格值域创建样式: {min_val} - {max_val}")
                            
                            sld_content = geoserver._create_default_raster_sld(min_val, max_val)
                            if geoserver.create_style(style_name, sld_content):
                                logger.info(f"样式 {style_name} 创建成功，开始应用到图层")
                                if geoserver.apply_style_to_layer(layer_name, style_name):
                                    logger.info(f"✅ 样式已成功应用到图层 {layer_name}")
                                else:
                                    logger.warning(f"⚠️ 样式应用到图层失败，但图层已发布")
                            else:
                                logger.warning(f"⚠️ 样式创建失败，但图层已发布")
                            
                            wms_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}&format=image/png&transparent=true"
                            
                            if 'risk_layer' not in raster_metadata:
                                raster_metadata['risk_layer'] = {}
                            
                            raster_metadata['risk_layer'].update({
                                'wms_url': wms_url,
                                'published': True
                            })
                            
                            published_layers['risk_layer'] = {
                                'layer_name': layer_name,
                                'wms_url': wms_url
                            }
                            logger.info(f"✅ 风险栅格图层重新发布成功: {layer_name}")
                        else:
                            error_msg = f"图层 {layer_name} 发布后验证失败（图层在GeoServer中不存在，实际图层名称: {actual_layer_name}）"
                            logger.error(f"❌ {error_msg}")
                            error_messages.append(error_msg)
                    else:
                        error_msg = f"风险栅格图层发布失败: {layer_name}（publish_raster返回False）"
                        logger.error(f"❌ {error_msg}")
                        error_messages.append(error_msg)
                else:
                    error_msg = f"风险栅格文件不存在: {risk_file_path}"
                    logger.error(f"❌ {error_msg}")
                    error_messages.append(error_msg)
            else:
                error_msg = "任务没有关联的风险栅格文件"
                logger.warning(f"⚠️ {error_msg}")
                error_messages.append(error_msg)
            
            # 发布影响栅格
            if task.impact_raster_file:
                impact_file_path = task.impact_raster_file.path
                if os.path.exists(impact_file_path):
                    layer_name = f"impact_layer_{task.id}"
                    logger.info(f"开始重新发布影响栅格图层: {layer_name}")
                    logger.info(f"栅格文件路径: {impact_file_path}")
                    
                    # 先删除可能存在的旧图层（如果名称不同）
                    try:
                        full_layer_name = f"{geoserver.workspace}:{layer_name}"
                        old_layer_check = geoserver.get_layer_info(full_layer_name)
                        if old_layer_check:
                            logger.info(f"发现旧图层 {layer_name}，尝试删除")
                            # 尝试通过GeoServer REST API删除图层
                            try:
                                delete_url = f"{geoserver.base_url}/rest/layers/{full_layer_name}.json"
                                import requests
                                response = requests.delete(delete_url, auth=geoserver.auth, timeout=30)
                                if response.status_code in [200, 204]:
                                    logger.info(f"旧图层 {layer_name} 删除成功")
                                else:
                                    logger.warning(f"删除旧图层返回状态码: {response.status_code}")
                            except Exception as del_error:
                                logger.warning(f"删除旧图层时出错: {del_error}")
                            time.sleep(1)
                    except Exception as e:
                        logger.warning(f"检查旧图层时出错（可能不存在）: {e}")
                    
                    publish_result = geoserver.publish_raster(coverage_store_name, layer_name, impact_file_path)
                    logger.info(f"publish_raster 返回结果: {publish_result}")
                    
                    if publish_result:
                        # 等待一下让GeoServer处理
                        time.sleep(3)  # 增加等待时间，确保重命名完成
                        
                        # 验证图层是否存在（先尝试期望的名称）
                        full_layer_name = f"{geoserver.workspace}:{layer_name}"
                        layer_check = geoserver.get_layer_info(full_layer_name)
                        logger.info(f"图层验证结果（期望名称 {layer_name}）: {layer_check is not None}")
                        
                        # 如果期望名称的图层不存在，尝试查找实际创建的图层名称（可能是CoverageStore名称）
                        actual_layer_name = layer_name
                        if not layer_check:
                            logger.info(f"⚠️ 期望图层名称 {layer_name} 不存在，尝试查找实际创建的图层...")
                            # 检查CoverageStore中的Coverage名称
                            try:
                                coverage_list = geoserver._make_request('GET', f'workspaces/{geoserver.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                                if coverage_list and 'coverages' in coverage_list:
                                    coverages = coverage_list['coverages'].get('coverage', [])
                                    if isinstance(coverages, list) and len(coverages) > 0:
                                        coverage_obj = coverages[0]
                                        if isinstance(coverage_obj, dict):
                                            actual_layer_name = coverage_obj.get('name', layer_name)
                                        else:
                                            actual_layer_name = coverage_store_name  # 使用CoverageStore名称
                                    elif isinstance(coverages, dict):
                                        actual_layer_name = coverages.get('name', layer_name)
                                    else:
                                        actual_layer_name = coverage_store_name  # 使用CoverageStore名称
                                    
                                    logger.info(f"找到实际图层名称: {actual_layer_name}")
                                    # 验证实际图层是否存在
                                    full_actual_name = f"{geoserver.workspace}:{actual_layer_name}"
                                    layer_check = geoserver.get_layer_info(full_actual_name)
                                    if layer_check:
                                        logger.info(f"✅ 找到实际创建的图层: {actual_layer_name}")
                                        layer_name = actual_layer_name  # 使用实际图层名称
                                    else:
                                        logger.warning(f"⚠️ 实际图层名称 {actual_layer_name} 也不存在，可能GeoServer尚未完全处理")
                            except Exception as e:
                                logger.warning(f"⚠️ 查找实际图层名称时出错: {e}")
                        
                        if layer_check:
                            # 为图层创建并应用默认样式
                            style_name = f"{layer_name}_style"
                            logger.info(f"为图层 {layer_name} 创建样式: {style_name}")
                            
                            # 从栅格文件读取统计信息，以创建合适的样式
                            # 快速模式：使用默认值域，避免长时间读取栅格数据
                            logger.info(f"快速模式：使用默认值域创建样式（避免长时间读取栅格数据）")
                            min_val, max_val = (0.0, 5.0)
                            
                            # 可选：尝试快速读取统计信息（不阻塞）
                            try:
                                import threading
                                result = [None]
                                def quick_get_stats():
                                    try:
                                        result[0] = geoserver._get_raster_statistics(impact_file_path)
                                    except:
                                        pass
                                
                                thread = threading.Thread(target=quick_get_stats)
                                thread.daemon = True
                                thread.start()
                                thread.join(timeout=3)  # 3秒超时
                                
                                if result[0] and not thread.is_alive():
                                    min_val, max_val = result[0]
                                    logger.info(f"✅ 快速获取到统计信息，更新值域: {min_val} - {max_val}")
                            except:
                                pass
                            
                            logger.info(f"使用栅格值域创建样式: {min_val} - {max_val}")
                            
                            sld_content = geoserver._create_default_raster_sld(min_val, max_val)
                            if geoserver.create_style(style_name, sld_content):
                                logger.info(f"样式 {style_name} 创建成功，开始应用到图层")
                                if geoserver.apply_style_to_layer(layer_name, style_name):
                                    logger.info(f"✅ 样式已成功应用到图层 {layer_name}")
                                else:
                                    logger.warning(f"⚠️ 样式应用到图层失败，但图层已发布")
                            else:
                                logger.warning(f"⚠️ 样式创建失败，但图层已发布")
                            
                            wms_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{layer_name}&format=image/png&transparent=true"
                            
                            if 'impact_layer' not in raster_metadata:
                                raster_metadata['impact_layer'] = {}
                            
                            raster_metadata['impact_layer'].update({
                                'wms_url': wms_url,
                                'published': True
                            })
                            
                            published_layers['impact_layer'] = {
                                'layer_name': layer_name,
                                'wms_url': wms_url
                            }
                            logger.info(f"✅ 影响栅格图层重新发布成功: {layer_name}")
                        else:
                            error_msg = f"图层 {layer_name} 发布后验证失败（图层在GeoServer中不存在，实际图层名称: {actual_layer_name}）"
                            logger.error(f"❌ {error_msg}")
                            error_messages.append(error_msg)
                    else:
                        error_msg = f"影响栅格图层发布失败: {layer_name}（publish_raster返回False）"
                        logger.error(f"❌ {error_msg}")
                        error_messages.append(error_msg)
                else:
                    error_msg = f"影响栅格文件不存在: {impact_file_path}"
                    logger.error(f"❌ {error_msg}")
                    error_messages.append(error_msg)
            else:
                error_msg = "任务没有关联的影响栅格文件"
                logger.warning(f"⚠️ {error_msg}")
                error_messages.append(error_msg)
            
            # 检查是否有成功发布的图层
            if not published_layers or len(published_layers) == 0:
                error_detail = '没有图层成功发布。'
                if error_messages:
                    error_detail += ' 失败原因: ' + '; '.join(error_messages)
                else:
                    error_detail += ' 请检查后端日志和GeoServer状态'
                
                logger.error(f"❌ {error_detail}")
                return Response({
                    'error': error_detail,
                    'error_details': error_messages,
                    'published_layers': {},
                    'updated_metadata': raster_metadata
                }, status=500)
            
            # 更新任务的栅格图层元数据
            task.raster_layers_metadata = raster_metadata
            task.save()
            
            # 更新分析结果中的栅格图层信息
            if task.analysis_results and 'raster_layers' in task.analysis_results:
                for key in published_layers:
                    if key in task.analysis_results['raster_layers']:
                        task.analysis_results['raster_layers'][key].update(published_layers[key])
                task.save()
            
            logger.info(f"✅ 重新发布完成，成功发布 {len(published_layers)} 个图层: {list(published_layers.keys())}")
            return Response({
                'message': f'栅格图层重新发布成功，共发布 {len(published_layers)} 个图层',
                'published_layers': published_layers,
                'updated_metadata': raster_metadata
            })
            
        except Exception as e:
            logger.error(f"重新发布栅格图层失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'error': f'重新发布失败: {str(e)}'
            }, status=500)
    
    @action(detail=False, methods=['post'], url_path='upload-ecology-raster', parser_classes=[MultiPartParser, FormParser])
    def upload_ecology_raster(self, request):
        """上传生态指数栅格数据"""
        # 最简化测试版本
        logger.info("=== 收到上传请求 ===")
        
        try:
            logger.info(f"请求方法: {request.method}")
            logger.info(f"Content-Type: {request.content_type}")
            logger.info(f"FILES: {list(request.FILES.keys())}")
            
            if 'file' not in request.FILES:
                logger.warning("未找到上传文件")
                return Response({
                    'success': False,
                    'message': '未找到上传文件'
                }, status=400)
            
            uploaded_file = request.FILES['file']
            file_name = uploaded_file.name
            logger.info(f"接收到文件: {file_name}, 大小: {uploaded_file.size} bytes")
            
            # 验证文件类型
            if not file_name.lower().endswith(('.tif', '.tiff')):
                return Response({
                    'success': False,
                    'message': '仅支持GeoTIFF格式 (.tif, .tiff)'
                }, status=400)
            
            # 验证文件大小（最大100MB）
            if uploaded_file.size > 1024 * 1024 * 1024:
                return Response({
                    'success': False,
                    'message': '文件大小超过1GB限制'
                }, status=400)
            
            # 保存文件
            import os
            from django.conf import settings
            
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_projects')
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"上传目录: {upload_dir}")
            
            # 使用固定文件名以便覆盖旧数据
            save_path = os.path.join(upload_dir, 'ecology_raster.tif')
            
            # 保存上传的文件
            logger.info(f"开始保存文件到: {save_path}")
            with open(save_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            logger.info(f"✅ 生态栅格文件已保存: {save_path}")
            
            # 发布到GeoServer
            logger.info("🚀 开始发布到GeoServer...")
            try:
                from .geoserver_config import geoserver_manager
                
                logger.info(f"调用publish_raster: coverage_store=ecology_raster, layer=ecology_raster, file={save_path}")
                success = geoserver_manager.publish_raster(
                    coverage_store_name='ecology_raster',
                    layer_name='ecology_raster',
                    file_path=save_path
                )
                logger.info(f"publish_raster返回值: {success}")
                
                if success:
                    logger.info("✅ GeoServer发布成功")
                    return Response({
                        'success': True,
                        'message': '生态指数栅格上传成功并已发布到GeoServer',
                        'file_name': file_name,
                        'layer_name': 'ecology_raster'
                    })
                else:
                    logger.warning("⚠️ GeoServer发布失败")
                    return Response({
                        'success': True,
                        'message': '文件上传成功，但GeoServer发布失败。请手动在GeoServer中发布或检查GeoServer连接',
                        'file_name': file_name,
                        'save_path': save_path
                    })
            except Exception as geo_error:
                logger.error(f"GeoServer发布异常: {str(geo_error)}")
                import traceback
                logger.error(traceback.format_exc())
                return Response({
                    'success': True,
                    'message': f'文件上传成功，但GeoServer发布失败: {str(geo_error)}。文件已保存，可稍后手动发布',
                    'file_name': file_name,
                    'save_path': save_path
                })
                
        except Exception as e:
            logger.error(f"❌ 上传生态栅格失败: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"错误堆栈:\n{error_trace}")
            
            # 返回更详细的错误信息
            error_message = str(e)
            if hasattr(e, '__cause__') and e.__cause__:
                error_message = f"{error_message} (原因: {str(e.__cause__)})"
            
            return Response({
                'success': False,
                'message': f'上传失败: {error_message}',
                'error_detail': error_trace[:500] if len(error_trace) > 500 else error_trace  # 限制长度
            }, status=500)
    
    @action(detail=False, methods=['post'], url_path='upload-economy-vector', parser_classes=[MultiPartParser, FormParser])
    def upload_economy_vector(self, request):
        """上传经济数据矢量"""
        try:
            if 'file' not in request.FILES:
                return Response({
                    'success': False,
                    'message': '未找到上传文件'
                }, status=400)
            
            uploaded_file = request.FILES['file']
            file_name = uploaded_file.name
            
            # 验证文件类型
            if not file_name.lower().endswith('.zip'):
                return Response({
                    'success': False,
                    'message': '仅支持Shapefile压缩包 (.zip)'
                }, status=400)
            
            # 验证文件大小
            if uploaded_file.size > 1024 * 1024 * 1024:
                return Response({
                    'success': False,
                    'message': '文件大小超过1GB限制'
                }, status=400)
            
            # 保存文件
            import os
            import zipfile
            from django.conf import settings
            
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_projects', 'economy_vector')
            os.makedirs(upload_dir, exist_ok=True)
            
            zip_path = os.path.join(upload_dir, 'economy_vector.zip')
            
            # 保存ZIP文件
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            is_valid_zip, zip_message = validate_shapefile_zip(zip_path)
            if not is_valid_zip:
                return Response({
                    'success': False,
                    'message': zip_message
                }, status=400)
            
            logger.info(f"经济矢量ZIP文件已保存: {zip_path}")
            
            # 解压文件
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(upload_dir)
                logger.info(f"文件已解压到: {upload_dir}")
            except Exception as e:
                return Response({
                    'success': False,
                    'message': f'解压文件失败: {str(e)}'
                }, status=400)
            
            # 查找.shp文件
            shp_files = [f for f in os.listdir(upload_dir) if f.endswith('.shp')]
            if not shp_files:
                return Response({
                    'success': False,
                    'message': 'ZIP文件中未找到.shp文件'
                }, status=400)
            
            original_shp_name = shp_files[0]
            original_base_name = os.path.splitext(original_shp_name)[0]
            
            # 固定文件名
            fixed_name = 'economy_vector'
            fixed_shp_path = os.path.join(upload_dir, f'{fixed_name}.shp')
            
            # 如果文件名不是固定名称，重命名所有相关文件
            if original_base_name != fixed_name:
                logger.info(f"检测到文件名不匹配: {original_base_name} -> {fixed_name}，开始重命名...")
                
                # Shapefile需要重命名的文件扩展名
                shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
                
                for ext in shapefile_extensions:
                    old_file = os.path.join(upload_dir, f'{original_base_name}{ext}')
                    new_file = os.path.join(upload_dir, f'{fixed_name}{ext}')
                    
                    if os.path.exists(old_file):
                        # 如果目标文件已存在，先删除
                        if os.path.exists(new_file):
                            os.remove(new_file)
                            logger.info(f"  删除旧文件: {new_file}")
                        
                        # 重命名文件
                        os.rename(old_file, new_file)
                        logger.info(f"  重命名: {original_base_name}{ext} -> {fixed_name}{ext}")
                
                logger.info(f"✅ 文件重命名完成: {original_base_name} -> {fixed_name}")
            
            shp_path = fixed_shp_path
            
            # 检查是否存在.cpg文件，如果不存在则创建GBK编码
            cpg_path = os.path.join(upload_dir, f'{fixed_name}.cpg')
            if not os.path.exists(cpg_path):
                with open(cpg_path, 'w') as f:
                    f.write('GBK')
                logger.info(f"创建 .cpg 文件（GBK编码）: {cpg_path}")
            else:
                # 读取现有.cpg文件内容
                with open(cpg_path, 'r') as f:
                    cpg_encoding = f.read().strip()
                logger.info(f"使用现有 .cpg 文件编码: {cpg_encoding}")
            
            logger.info(f"✅ 经济矢量数据已准备就绪: {shp_path}")
            
            # 发布到GeoServer并生成样式
            publish_success = False
            try:
                from .geoserver_config import geoserver_manager
                
                # 1. 发布Shapefile到GeoServer
                logger.info("正在发布到GeoServer...")
                # 读取.cpg文件获取编码
                encoding = cpg_encoding if 'cpg_encoding' in locals() else 'GBK'
                
                publish_success = geoserver_manager.publish_shapefile(
                    layer_name='economy_vector',
                    shapefile_path=shp_path,
                    charset=encoding
                )
                
                if publish_success:
                    logger.info("✅ 成功发布到GeoServer")
                    
                    # 2. 读取矢量数据统计信息并生成样式
                    try:
                        min_val, max_val, mean_val = geoserver_manager._get_vector_statistics(shp_path, 'GDP')
                        
                        if min_val is not None and max_val is not None:
                            logger.info(f"GDP统计信息: min={min_val}, max={max_val}, mean={mean_val}")
                            
                            # 根据数据分布生成样式
                            style_name = 'economy_vector'
                            sld_content = geoserver_manager._create_vector_sld_by_attribute(
                                field_name='GDP',
                                min_val=min_val,
                                max_val=max_val,
                                color_scheme='default'  # 黄-橙-红配色
                            )
                            
                            # 删除旧样式（如果存在）
                            try:
                                geoserver_manager.delete_style(style_name)
                            except:
                                pass
                            
                            # 创建并应用新样式
                            if geoserver_manager.create_style(style_name, sld_content):
                                geoserver_manager.apply_style_to_layer('economy_vector', style_name)
                                logger.info(f"✅ 经济矢量样式已自动生成并应用")
                        else:
                            logger.warning("无法读取GDP统计信息，使用默认样式")
                    except Exception as e:
                        logger.warning(f"生成矢量样式失败: {e}，使用默认样式")
                else:
                    logger.error("❌ 发布到GeoServer失败")
            except Exception as e:
                logger.error(f"发布到GeoServer时出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 返回结果
            if publish_success:
                return Response({
                    'success': True,
                    'message': '经济数据矢量上传并发布成功！',
                    'file_name': file_name,
                    'shp_path': shp_path,
                    'layer_name': 'economy_vector'
                })
            else:
                return Response({
                    'success': True,
                    'message': '经济数据矢量上传成功，但发布到GeoServer失败。请检查GeoServer服务状态。',
                    'file_name': file_name,
                    'shp_path': shp_path,
                    'warning': 'GeoServer发布失败'
                })
                
        except Exception as e:
            logger.error(f"上传经济矢量失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'message': f'上传失败: {str(e)}'
            }, status=500)
    
    @action(detail=False, methods=['post'], url_path='upload-engineering-vector', parser_classes=[MultiPartParser, FormParser])
    def upload_engineering_vector(self, request):
        """上传工程项目矢量"""
        try:
            if 'file' not in request.FILES:
                return Response({
                    'success': False,
                    'message': '未找到上传文件'
                }, status=400)
            
            uploaded_file = request.FILES['file']
            file_name = uploaded_file.name
            
            # 验证文件类型
            if not file_name.lower().endswith('.zip'):
                return Response({
                    'success': False,
                    'message': '仅支持Shapefile压缩包 (.zip)'
                }, status=400)
            
            # 验证文件大小
            if uploaded_file.size > 1024 * 1024 * 1024:
                return Response({
                    'success': False,
                    'message': '文件大小超过1GB限制'
                }, status=400)
            
            # 保存文件
            import os
            import zipfile
            from django.conf import settings
            
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_projects', 'engineering_vector')
            os.makedirs(upload_dir, exist_ok=True)
            
            zip_path = os.path.join(upload_dir, 'engineering_vector.zip')
            
            # 保存ZIP文件
            with open(zip_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            is_valid_zip, zip_message = validate_shapefile_zip(zip_path)
            if not is_valid_zip:
                return Response({
                    'success': False,
                    'message': zip_message
                }, status=400)
            
            logger.info(f"工程矢量ZIP文件已保存: {zip_path}")
            
            # 解压文件
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(upload_dir)
                logger.info(f"文件已解压到: {upload_dir}")
            except Exception as e:
                return Response({
                    'success': False,
                    'message': f'解压文件失败: {str(e)}'
                }, status=400)
            
            # 查找.shp文件
            shp_files = [f for f in os.listdir(upload_dir) if f.endswith('.shp')]
            if not shp_files:
                return Response({
                    'success': False,
                    'message': 'ZIP文件中未找到.shp文件'
                }, status=400)
            
            original_shp_name = shp_files[0]
            original_base_name = os.path.splitext(original_shp_name)[0]
            
            # 固定文件名
            fixed_name = 'engineering_vector'
            fixed_shp_path = os.path.join(upload_dir, f'{fixed_name}.shp')
            
            # 如果文件名不是固定名称，重命名所有相关文件
            if original_base_name != fixed_name:
                logger.info(f"检测到文件名不匹配: {original_base_name} -> {fixed_name}，开始重命名...")
                
                # Shapefile需要重命名的文件扩展名
                shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
                
                for ext in shapefile_extensions:
                    old_file = os.path.join(upload_dir, f'{original_base_name}{ext}')
                    new_file = os.path.join(upload_dir, f'{fixed_name}{ext}')
                    
                    if os.path.exists(old_file):
                        # 如果目标文件已存在，先删除
                        if os.path.exists(new_file):
                            os.remove(new_file)
                            logger.info(f"  删除旧文件: {new_file}")
                        
                        # 重命名文件
                        os.rename(old_file, new_file)
                        logger.info(f"  重命名: {original_base_name}{ext} -> {fixed_name}{ext}")
                
                logger.info(f"✅ 文件重命名完成: {original_base_name} -> {fixed_name}")
            
            shp_path = fixed_shp_path
            
            # 检查是否存在.cpg文件，如果不存在则创建GBK编码
            cpg_path = os.path.join(upload_dir, f'{fixed_name}.cpg')
            if not os.path.exists(cpg_path):
                with open(cpg_path, 'w') as f:
                    f.write('GBK')
                logger.info(f"创建 .cpg 文件（GBK编码）: {cpg_path}")
            else:
                # 读取现有.cpg文件内容
                with open(cpg_path, 'r') as f:
                    cpg_encoding = f.read().strip()
                logger.info(f"使用现有 .cpg 文件编码: {cpg_encoding}")
            
            logger.info(f"✅ 工程矢量数据已准备就绪: {shp_path}")
            
            # 发布到GeoServer并生成样式
            publish_success = False
            try:
                from .geoserver_config import geoserver_manager
                import random
                
                # 1. 发布Shapefile到GeoServer
                logger.info("正在发布到GeoServer...")
                # 读取.cpg文件获取编码
                encoding = cpg_encoding if 'cpg_encoding' in locals() else 'GBK'
                
                publish_success = geoserver_manager.publish_shapefile(
                    layer_name='engineering_vector',
                    shapefile_path=shp_path,
                    charset=encoding
                )
                
                if publish_success:
                    logger.info("✅ 成功发布到GeoServer")
                    
                    # 2. 为工程矢量生成动态样式（使用蓝色系统一样式）
                    try:
                        # 为每次上传生成稍有不同的蓝色调
                        blue_shades = [
                            ('#0000FF', 0.3),  # 纯蓝
                            ('#0066FF', 0.35), # 亮蓝
                            ('#0099FF', 0.3),  # 天蓝
                            ('#3366FF', 0.35), # 中蓝
                        ]
                        color, opacity = random.choice(blue_shades)
                        
                        style_name = 'engineering_vector'
                        sld_content = geoserver_manager._create_vector_sld_simple(
                            color=color,
                            opacity=opacity
                        )
                        
                        # 删除旧样式（如果存在）
                        try:
                            geoserver_manager.delete_style(style_name)
                        except:
                            pass
                        
                        # 创建并应用新样式
                        if geoserver_manager.create_style(style_name, sld_content):
                            geoserver_manager.apply_style_to_layer('engineering_vector', style_name)
                            logger.info(f"✅ 工程矢量样式已生成（{color}）")
                    except Exception as e:
                        logger.warning(f"生成工程矢量样式失败: {e}，使用默认样式")
                else:
                    logger.error("❌ 发布到GeoServer失败")
            except Exception as e:
                logger.error(f"发布到GeoServer时出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 返回结果
            if publish_success:
                return Response({
                    'success': True,
                    'message': '工程项目矢量上传并发布成功！',
                    'file_name': file_name,
                    'shp_path': shp_path,
                    'layer_name': 'engineering_vector'
                })
            else:
                return Response({
                    'success': True,
                    'message': '工程项目矢量上传成功，但发布到GeoServer失败。请检查GeoServer服务状态。',
                    'file_name': file_name,
                    'shp_path': shp_path,
                    'warning': 'GeoServer发布失败'
                })
                
        except Exception as e:
            logger.error(f"上传工程矢量失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'message': f'上传失败: {str(e)}'
            }, status=500)
