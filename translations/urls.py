from django.urls import path, include
from rest_framework.routers import DefaultRouter
from translations.views import TextTranslationViewSet

router = DefaultRouter()
router.register(r'translations', TextTranslationViewSet)

app_name = 'translations'
urlpatterns = [path('', include(router.urls))]
