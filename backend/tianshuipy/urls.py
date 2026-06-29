"""
URL configuration for tianshuipy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.views.generic.base import RedirectView
import logging

logger = logging.getLogger(__name__)

try:
    from rest_framework.documentation import include_docs_urls
except Exception as exc:
    include_docs_urls = None
    logger.warning(f"REST framework docs 不可用，将跳过 /api/docs/ 路由: {exc}")

def home_view(request):
    """首页视图 - 显示系统信息"""
    return render(request, 'index.html')

def overlay_analysis_demo_view(request):
    """叠加分析演示页面"""
    return render(request, 'overlay_analysis_demo.html')

urlpatterns = [
    path("", home_view, name="home"),  # 根路径显示首页
    path("admin/", admin.site.urls),
    path("overlay-analysis-demo/", overlay_analysis_demo_view, name="overlay-analysis-demo"),  # 叠加分析演示页面
    path("api/v1/", include([
        path("users/", include('users.urls')),
        path("environment/", include('environment.urls')),
    ])),
    path("api/", RedirectView.as_view(url='/api/v1/', permanent=False)),
]

if include_docs_urls is not None:
    try:
        urlpatterns.append(
            path("api/docs/", include_docs_urls(title='天水平台 API 文档'), name="api-docs")
        )
    except Exception as exc:
        logger.warning(f"REST framework docs 初始化失败，已跳过 /api/docs/ 路由: {exc}")

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
