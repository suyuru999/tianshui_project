from rest_framework import serializers
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
from users.serializers import UserSerializer


class RemoteSensingImageSerializer(serializers.ModelSerializer):
    """遥感影像序列化器"""
    uploaded_by = UserSerializer(read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    processing_status_display = serializers.CharField(source='get_processing_status_display', read_only=True)
    
    class Meta:
        model = RemoteSensingImage
        fields = [
            'id', 'name', 'description', 'image_type', 'file_path', 'thumbnail',
            'center_lat', 'center_lon', 'acquisition_date', 'processing_date',
            'resolution', 'bands_count', 'file_size', 'file_size_mb',
            'is_processed', 'processing_status', 'processing_status_display',
            'uploaded_by'
        ]
        read_only_fields = ['id', 'processing_date', 'file_size', 'uploaded_by']
    
    def get_file_size_mb(self, obj):
        """获取文件大小（MB）"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


class EcologicalIndexSerializer(serializers.ModelSerializer):
    """生态指数序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    index_type_display = serializers.CharField(source='get_index_type_display', read_only=True)
    
    class Meta:
        model = EcologicalIndex
        fields = [
            'id', 'remote_sensing_image', 'index_type', 'index_type_display',
            'result_file', 'visualization_file', 'min_value', 'max_value',
            'mean_value', 'std_value', 'excellent_area', 'good_area',
            'moderate_area', 'poor_area', 'bad_area', 'processing_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RSEIResultSerializer(serializers.ModelSerializer):
    """RSEI结果序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    greenness = EcologicalIndexSerializer(read_only=True)
    wetness = EcologicalIndexSerializer(read_only=True)
    dryness = EcologicalIndexSerializer(read_only=True)
    heat = EcologicalIndexSerializer(read_only=True)
    rsei_result = EcologicalIndexSerializer(read_only=True)
    
    class Meta:
        model = RSEIResult
        fields = [
            'id', 'remote_sensing_image', 'greenness', 'wetness', 'dryness', 'heat',
            'rsei_result', 'pc1_variance', 'pc2_variance', 'pc3_variance', 'pc4_variance',
            'greenness_weight', 'wetness_weight', 'dryness_weight', 'heat_weight',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProcessingTaskSerializer(serializers.ModelSerializer):
    """处理任务序列化器"""
    remote_sensing_image = RemoteSensingImageSerializer(read_only=True)
    remote_sensing_image_id = serializers.UUIDField(write_only=True)  # 添加ID字段用于创建
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProcessingTask
        fields = [
            'id', 'remote_sensing_image', 'remote_sensing_image_id', 'task_type', 'status', 'status_display',
            'progress', 'current_step', 'error_message',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']
        
    def create(self, validated_data):
        """处理remote_sensing_image_id字段"""
        remote_sensing_image_id = validated_data.pop('remote_sensing_image_id')
        remote_sensing_image = RemoteSensingImage.objects.get(id=remote_sensing_image_id)
        return ProcessingTask.objects.create(
            remote_sensing_image=remote_sensing_image,
            **validated_data
        )


class RemoteSensingImageUploadSerializer(serializers.ModelSerializer):
    """遥感影像上传序列化器"""
    file = serializers.FileField(write_only=True)  # 添加file字段用于文件上传
    
    class Meta:
        model = RemoteSensingImage
        fields = ['id', 'name', 'description', 'image_type', 'file', 'acquisition_date', 'center_lat', 'center_lon']
        read_only_fields = ['id']  # id字段为只读，由Django自动生成
    
    def create(self, validated_data):
        """重写create方法，将file字段映射到file_path"""
        file_obj = validated_data.pop('file')
        validated_data['file_path'] = file_obj
        return super().create(validated_data)
    
    def validate_file(self, value):
        """验证文件格式"""
        if not value:
            raise serializers.ValidationError("文件不能为空")
            
        allowed_extensions = ['.tif', '.tiff', '.img', '.hdf', '.nc', '.zip', '.jpg', '.jpeg', '.png']
        file_extension = value.name.lower()
        
        if not any(file_extension.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小（900MB限制）
        if value.size > 900 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过900MB")
        
        return value
    
    def validate(self, data):
        """整体验证"""
        # 确保必需字段存在
        required_fields = ['name', 'image_type', 'acquisition_date', 'center_lat', 'center_lon']
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError(f"字段 {field} 是必需的")
        
        # 验证坐标范围
        if data.get('center_lat') and (data['center_lat'] < -90 or data['center_lat'] > 90):
            raise serializers.ValidationError("纬度必须在-90到90之间")
        
        if data.get('center_lon') and (data['center_lon'] < -180 or data['center_lon'] > 180):
            raise serializers.ValidationError("经度必须在-180到180之间")
        
        return data


class EcologicalIndexCalculationSerializer(serializers.Serializer):
    """生态指数计算请求序列化器"""
    remote_sensing_image_id = serializers.UUIDField()
    indices = serializers.ListField(
        child=serializers.ChoiceField(choices=EcologicalIndex.INDEX_TYPE_CHOICES),
        min_length=1
    )
    
    def validate_remote_sensing_image_id(self, value):
        """验证遥感影像是否存在"""
        try:
            RemoteSensingImage.objects.get(id=value)
        except RemoteSensingImage.DoesNotExist:
            raise serializers.ValidationError("指定的遥感影像不存在")
        return value


class RSEICalculationSerializer(serializers.Serializer):
    """RSEI计算请求序列化器"""
    remote_sensing_image_id = serializers.UUIDField()
    
    def validate_remote_sensing_image_id(self, value):
        """验证遥感影像是否存在"""
        try:
            RemoteSensingImage.objects.get(id=value)
        except RemoteSensingImage.DoesNotExist:
            raise serializers.ValidationError("指定的遥感影像不存在")
        return value


class EcologicalIndexStatisticsSerializer(serializers.Serializer):
    """生态指数统计信息序列化器"""
    index_type = serializers.CharField()
    total_area = serializers.FloatField()
    excellent_percentage = serializers.FloatField()
    good_percentage = serializers.FloatField()
    moderate_percentage = serializers.FloatField()
    poor_percentage = serializers.FloatField()
    bad_percentage = serializers.FloatField()
    mean_value = serializers.FloatField()
    std_value = serializers.FloatField() 


class CitizenFeedbackSerializer(serializers.ModelSerializer):
    """民众意见反馈序列化器"""
    created_by = UserSerializer(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = CitizenFeedback
        fields = ['id', 'category', 'category_display', 'title', 'content', 'contact', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class ClimateDataFileSerializer(serializers.ModelSerializer):
    """气候数据文件序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    uploaded_by_username = serializers.SerializerMethodField()
    
    def get_uploaded_by_username(self, obj):
        """安全获取上传用户名"""
        return obj.uploaded_by.username if obj.uploaded_by else None
    
    class Meta:
        model = ClimateDataFile
        fields = [
            'id', 'name', 'file', 'file_type', 'description', 'status', 'status_display',
            'uploaded_by', 'uploaded_by_username', 'created_at', 'processed_at', 'error_message'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'processed_at']


class ClimateDataFileUploadSerializer(serializers.ModelSerializer):
    """气候数据文件上传序列化器"""
    
    class Meta:
        model = ClimateDataFile
        fields = ['name', 'file', 'description']
    
    def validate_file(self, value):
        """验证文件类型"""
        if not value.name.lower().endswith(('.csv', '.xlsx', '.xls')):
            raise serializers.ValidationError("只支持CSV和Excel文件格式")
        return value


class ClimateAnalysisResultSerializer(serializers.ModelSerializer):
    """气候分析结果序列化器"""
    data_file_name = serializers.CharField(source='data_file.name', read_only=True)
    
    class Meta:
        model = ClimateAnalysisResult
        fields = [
            'id', 'data_file', 'data_file_name', 'analysis_type',
            'temperature_avg', 'temperature_max', 'temperature_min', 'temperature_std',
            'precipitation_avg', 'precipitation_max', 'precipitation_min', 'precipitation_std',
            'humidity_avg', 'humidity_max', 'humidity_min', 'humidity_std',
            'wind_speed_avg', 'wind_speed_max', 'wind_speed_min', 'wind_speed_std',
            'chart_data', 'report_file', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClimateAnalysisRequestSerializer(serializers.Serializer):
    """气候分析请求序列化器"""
    file_id = serializers.UUIDField()
    analysis_type = serializers.ChoiceField(
        choices=[('comprehensive', '综合分析'), ('temperature', '温度分析'), ('precipitation', '降水分析')],
        default='comprehensive'
    )


class EcologicalIndexFileSerializer(serializers.ModelSerializer):
    """生态指数文件序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    uploaded_by_username = serializers.SerializerMethodField()
    
    def get_uploaded_by_username(self, obj):
        """安全获取上传用户名"""
        return obj.uploaded_by.username if obj.uploaded_by else None

    class Meta:
        model = EcologicalIndexFile
        fields = [
            'id', 'filename', 'file', 'description', 'status', 'status_display',
            'indices_data', 'timestamp', 'uploaded_by', 'uploaded_by_username',
            'created_at', 'processed_at', 'error_message'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'processed_at']


class EcologicalIndexFileUploadSerializer(serializers.ModelSerializer):
    """生态指数文件上传序列化器"""

    class Meta:
        model = EcologicalIndexFile
        fields = ['filename', 'file', 'description']

    def validate_file(self, value):
        """验证文件类型"""
        if not value.name.lower().endswith('.json'):
            raise serializers.ValidationError("只支持JSON文件格式")
        return value


class EcologicalProjectFileSerializer(serializers.ModelSerializer):
    """生态修复工程文件序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    uploaded_by_username = serializers.SerializerMethodField()
    
    def get_uploaded_by_username(self, obj):
        """安全获取上传用户名"""
        return obj.uploaded_by.username if obj.uploaded_by else None

    class Meta:
        model = EcologicalProjectFile
        fields = [
            'id', 'filename', 'file', 'description', 'status', 'status_display',
            'geojson_data', 'uploaded_by', 'uploaded_by_username',
            'created_at', 'processed_at', 'error_message'
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'processed_at']


class EcologicalProjectFileUploadSerializer(serializers.ModelSerializer):
    """生态修复工程文件上传序列化器"""

    class Meta:
        model = EcologicalProjectFile
        fields = ['filename', 'file', 'description']

    def validate_file(self, value):
        """验证文件类型"""
        if not value.name.lower().endswith('.json'):
            raise serializers.ValidationError("只支持JSON文件格式")
        return value


class OverlayAnalysisTaskSerializer(serializers.ModelSerializer):
    """叠加分析任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_overall_risk_level_display', read_only=True)
    ecological_index_file_name = serializers.CharField(source='ecological_index_file.filename', read_only=True)
    ecological_project_file_name = serializers.CharField(source='ecological_project_file.filename', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = OverlayAnalysisTask
        fields = [
            'id', 'name', 'description', 'ecological_index_file', 'ecological_project_file',
            'ecological_index_file_name', 'ecological_project_file_name',
            'status', 'status_display', 'progress', 'current_step',
            'analysis_results', 'overall_risk_level', 'risk_level_display',
            'error_message', 'created_by', 'created_by_username',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'started_at', 'completed_at']


class OverlayAnalysisTaskCreateSerializer(serializers.ModelSerializer):
    """叠加分析任务创建序列化器"""

    class Meta:
        model = OverlayAnalysisTask
        fields = ['id', 'name', 'description', 'ecological_index_file', 'ecological_project_file', 'status', 'progress']
        read_only_fields = ['id', 'status', 'progress']

    def validate(self, data):
        """验证关联文件状态"""
        ecological_index_file = data.get('ecological_index_file')
        ecological_project_file = data.get('ecological_project_file')

        if ecological_index_file and ecological_index_file.status not in ['uploaded', 'completed']:
            raise serializers.ValidationError("生态指数文件必须上传完成后才能进行叠加分析")

        if ecological_project_file and ecological_project_file.status not in ['uploaded', 'completed']:
            raise serializers.ValidationError("生态修复工程文件必须上传完成后才能进行叠加分析")

        return data