from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RemoteSensingImageViewSet,
    # EcologicalIndexViewSet,
    # RSEIResultViewSet,
    ProcessingTaskViewSet,
    simple_test,
    test_upload
)
# from .spatial_views import (
#     wms_capabilities,
#     wms_map,
#     wfs_capabilities,
#     spatial_layers,
#     publish_to_geoserver,
#     geoserver_status
# )

# 配置路由器，注册必要的视图集
router = DefaultRouter()
router.register(r'remote-sensing-images', RemoteSensingImageViewSet)
# router.register(r'ecological-indices', EcologicalIndexViewSet)
# router.register(r'rsei-results', RSEIResultViewSet)
router.register(r'processing-tasks', ProcessingTaskViewSet)

app_name = 'environment'

urlpatterns = [
    path('', include(router.urls)),  # 启用路由器
    
    # 测试路由
    path('simple/', simple_test, name='simple_test'),
    path('test-upload/', test_upload, name='test_upload'),
    
    # 暂时注释掉所有地理空间服务路由
    # path('spatial/wms/capabilities/', wms_capabilities, name='wms_capabilities'),
    # path('spatial/wms/map/', wms_map, name='wms_map'),
    # path('spatial/wfs/capabilities/', wfs_capabilities, name='wfs_capabilities'),
    # path('spatial/layers/', spatial_layers, name='spatial_layers'),
    # path('spatial/publish/', publish_to_geoserver, name='publish_to_geoserver'),
    # path('spatial/geoserver/status/', geoserver_status, name='geoserver_status'),
] 