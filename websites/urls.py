from django.urls import path, include
from rest_framework.routers import DefaultRouter
from websites.views import (
    WebsiteLangVersionViewSet,
    WebsiteVersionListOrCreateViewSet,
    WebsiteDomainViewSet,
    WebsiteDomainListOrCreateViewSet,
)


app_name = 'websites'
router = DefaultRouter()
router.register(r'website-versions', WebsiteVersionListOrCreateViewSet)
router.register(r'website-domains', WebsiteDomainListOrCreateViewSet)

website_versions_router = DefaultRouter()
website_versions_router.register(r'website-versions', WebsiteLangVersionViewSet)
website_versions_router.register(r'website-domains', WebsiteDomainViewSet)

urlpatterns = [
    path('projects/<uuid:guid>/', include(router.urls)),
    path('', include(website_versions_router.urls)),
]
