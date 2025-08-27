from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
# 使用空前缀，避免在项目路由 `api/v1/users/` 下出现重复的 `users` 段
router.register(r'', UserViewSet, basename='user')

app_name = 'users'

# 直接挂载到应用根，最终路径为 `/api/v1/users/...`
urlpatterns = [
    path('', include(router.urls)),
]