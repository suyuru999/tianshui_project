from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RemoteSensingImageViewSet,
    EcologicalIndexViewSet,
    RSEIResultViewSet,
    ProcessingTaskViewSet,
    CitizenFeedbackViewSet,
    ClimateDataFileViewSet,
    EcologicalIndexFileViewSet,
    EcologicalProjectFileViewSet,
    OverlayAnalysisTaskViewSet,
    calculate_ecological_structure_indices,
    calculate_ecological_stress_indices,
    upload_climate_data,
    analyze_climate_data_api,
    get_climate_analysis_results
)
from .spatial_views import (
    wms_capabilities,
    wms_map,
    wfs_capabilities,
    spatial_layers,
    publish_to_geoserver,
    geoserver_status
)

# 配置路由器，注册必要的视图集
router = DefaultRouter()
router.register(r'remote-sensing-images', RemoteSensingImageViewSet)
router.register(r'ecological-indices', EcologicalIndexViewSet)
router.register(r'rsei-results', RSEIResultViewSet)
router.register(r'processing-tasks', ProcessingTaskViewSet)
router.register(r'feedback', CitizenFeedbackViewSet)
router.register(r'climate-data-files', ClimateDataFileViewSet)
router.register(r'ecological-index-files', EcologicalIndexFileViewSet)
router.register(r'ecological-project-files', EcologicalProjectFileViewSet)
router.register(r'overlay-analysis-tasks', OverlayAnalysisTaskViewSet)

app_name = 'environment'

urlpatterns = [
    path('', include(router.urls)),  # 启用路由器
    
    
    # 生态环境指数计算API
    path('ecological-structure-indices/', calculate_ecological_structure_indices, name='calculate_ecological_structure_indices'),
    path('ecological-stress-indices/', calculate_ecological_stress_indices, name='calculate_ecological_stress_indices'),
    
    # 气候监测API
    path('climate-monitoring/upload/', upload_climate_data, name='upload_climate_data'),
    path('climate-monitoring/analyze/', analyze_climate_data_api, name='analyze_climate_data'),
    path('climate-monitoring/results/<uuid:task_id>/', get_climate_analysis_results, name='get_climate_analysis_results'),
    
    path('spatial/wms/capabilities/', wms_capabilities, name='wms_capabilities'),
    path('spatial/wms/map/', wms_map, name='wms_map'),
    path('spatial/wfs/capabilities/', wfs_capabilities, name='wfs_capabilities'),
    path('spatial/layers/', spatial_layers, name='spatial_layers'),
    path('spatial/publish/', publish_to_geoserver, name='publish_to_geoserver'),
    path('spatial/geoserver/status/', geoserver_status, name='geoserver_status'),
] 
