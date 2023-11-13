from django.urls import path, include
from rest_framework.routers import DefaultRouter
from pages.views import (
    PageViewSet,
    PageVersionViewSet,
    PageVersionListOrCreateViewSet,
)


app_name = 'pages'
router = DefaultRouter()
router.register(r'pages', PageViewSet)
router.register(r'page-versions', PageVersionListOrCreateViewSet)

page_version_router = DefaultRouter()
page_version_router.register(r'page-versions', PageVersionViewSet)


urlpatterns = [
    path('website-versions/<uuid:guid>/', include(router.urls)),
    path('', include(page_version_router.urls)),
]
