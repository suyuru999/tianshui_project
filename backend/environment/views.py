from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import os
import json
import logging

# 取消注释必要的导入
from .models import (
    RemoteSensingImage,
    EcologicalIndex,
    RSEIResult,
    ProcessingTask,
    CitizenFeedback,
    ClimateDataFile,
    ClimateAnalysisResult,
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
    EcologicalIndexFileSerializer,
    EcologicalIndexFileUploadSerializer,
    EcologicalProjectFileSerializer,
    EcologicalProjectFileUploadSerializer,
    OverlayAnalysisTaskSerializer,
    OverlayAnalysisTaskCreateSerializer
)
from .tasks import calculate_ecological_indices, calculate_rsei_only
from .gdal_land_use_analysis import LandUseAnalyzer  # 导入土地利用分析器
from .vector_rasterize import rasterize_shapefile_to_tiff
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
            
            # 启动Celery任务进行异步计算
            from .tasks import calculate_ecological_indices
            celery_task = calculate_ecological_indices.delay(str(image.id), normalized_indices)
            
            # 更新任务状态
            task.status = 'processing'
            task.save()
            
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

# 暂时注释掉其他视图类，只保留遥感影像视图集
# class EcologicalIndexViewSet(viewsets.ModelViewSet):
#     """生态指数视图集"""
#     pass

# class RSEIResultViewSet(viewsets.ModelViewSet):
#     """RSEI结果视图集"""
#     pass

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
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save(created_by=None)

@api_view(['POST'])
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
            analyzer = LandUseAnalyzer(raster_input)
            
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
            analyzer = LandUseAnalyzer(raster_input)
            
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
    
    # 2. 检查文件大小（限制为50MB）
    max_size = 50 * 1024 * 1024  # 50MB
    if file_obj.size > max_size:
        errors.append(f'文件大小不能超过50MB，当前大小: {file_obj.size / (1024*1024):.2f}MB')
    
    # 3. 检查文件是否为空
    if file_obj.size == 0:
        errors.append('文件不能为空')
    
    # 4. 检查文件类型
    file_name = file_obj.name.lower()
    if not file_name.endswith(('.csv', '.xlsx', '.xls')):
        errors.append('只支持CSV和Excel文件格式(.csv, .xlsx, .xls)')
    
    # 5. 检查文件名
    if not file_name or file_name.strip() == '':
        errors.append('文件名不能为空')
    
    # 6. 检查文件名长度
    if len(file_name) > 255:
        errors.append('文件名过长，不能超过255个字符')
    
    return errors

@api_view(['POST'])
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
    permission_classes = [AllowAny]

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
            logger.error(f"启动叠加分析失败: {str(e)}")
            instance.status = 'failed'
            instance.error_message = str(e)
            instance.save()

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