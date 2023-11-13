from rest_framework.viewsets import ModelViewSet
from languages.serializer import LanguageSerializer
from languages.models import Language
from rest_framework import filters


class LanguageViewSet(ModelViewSet):
    queryset = Language.objects.filter(available=True)
    serializer_class = LanguageSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']
    http_method_names = ['get']
    lookup_field = 'guid'
