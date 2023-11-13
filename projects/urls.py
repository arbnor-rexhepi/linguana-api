from django.urls import path, include
from rest_framework.routers import DefaultRouter
from projects.views import ProjectDisableTranslationView, ProjectViewSet, DomainCheck


app_name = 'projects'
router = DefaultRouter()
router.register(r'projects', ProjectViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('domain_check/', DomainCheck.as_view(), name='valid_domain'),
    path(
        'projects/<uuid:guid>/disable-translation/',
        ProjectDisableTranslationView.as_view(),
        name='disable_translation',
    ),
]
