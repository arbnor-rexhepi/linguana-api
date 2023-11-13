from django.urls import path, include
from rest_framework.routers import DefaultRouter
from website_redirects.views import (
    WebsiteRedirectListAndCreateViewSet,
    WebsiteRedirectViewSet,
)


app_name = 'websites_redirects'

router = DefaultRouter()
router.register(
    r'website-redirects', WebsiteRedirectListAndCreateViewSet, basename='redirects'
)

redirect_router = DefaultRouter()
redirect_router.register(
    r'website-redirects', WebsiteRedirectViewSet, basename='website-redirects'
)

urlpatterns = [
    path('projects/<uuid:guid>/', include(router.urls)),
    path('', include(redirect_router.urls)),
]
