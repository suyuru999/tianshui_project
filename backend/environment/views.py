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
import logging

# 取消注释必要的导入
from .models import (
    RemoteSensingImage, 
    EcologicalIndex, 
    RSEIResult, 
    ProcessingTask,
    CitizenFeedback
)
from .serializers import (
    RemoteSensingImageSerializer,
    EcologicalIndexSerializer,
    RSEIResultSerializer,
    ProcessingTaskSerializer,
    RemoteSensingImageUploadSerializer,
    EcologicalIndexCalculationSerializer,
    RSEICalculationSerializer,
    CitizenFeedbackSerializer
)
from .tasks import calculate_ecological_indices, calculate_rsei_only

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

@api_view(['GET'])
@permission_classes([AllowAny])
def simple_test(request):
    """最简单的测试视图"""
    return Response({'message': 'Simple test works!'})

@api_view(['POST'])
@permission_classes([AllowAny])
def test_upload(request):
    """测试上传视图，用于调试"""
    try:
        # 打印请求信息
        print("请求方法:", request.method)
        print("请求内容类型:", request.content_type)
        print("请求数据:", request.data)
        print("请求文件:", request.FILES)
        
        # 检查是否有文件
        if 'file' in request.FILES:
            file_obj = request.FILES['file']
            print("文件信息:", {
                'name': file_obj.name,
                'size': file_obj.size,
                'content_type': file_obj.content_type
            })
        
        # 返回成功响应
        return Response({
            'message': '测试上传成功',
            'data': request.data,
            'files': list(request.FILES.keys()) if request.FILES else []
        })
    except Exception as e:
        print("错误:", str(e))
        import traceback
        traceback.print_exc()
        return Response({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500) 