from rest_framework.viewsets import ModelViewSet
from commons.serializers import EmptySerializer
from pages.filters import CustomFilter, CustomSearchFilter, CustomOrderingFilter
from pages.import_export_services import export_csv_page_version_translations
from pages.models import Page, PageLangVersion
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from rest_framework import status, parsers
from pages.services import (
    get_parsed_page_version,
    word_count_of_page_versions,
    publish_page_version,
    soft_delete_page_version,
    sync_website_pages,
    parse_page,
    translate_page_version,
    page_version_words_count,
    sync_and_add_website_version_pages,
    unpublish_page_version,
)
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from pages.serializers import (
    PageImportSerializer,
    PageLangVersionPatchSerializer,
    PageSerializer,
    PageVersionCustomCodeSerializer,
    PageVersionBaseInputSerializer,
    PageVersionElementSerializer,
    PageVersionImportTranslationSerializer,
    PageVersionPublishSerializer,
    PageVersionSyncSerializer,
    PageVersionUnpublishSerializer,
    ParsedPageSerializer,
    PageLangVersionCreateSerializer,
    PageLangVersionListSerializer,
    PageLangVersionPublishSerializer,
)
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.decorators import action
from commons.throttles import CustomUserRateThrottle

from pages.selectors import (
    get_website_version_all_pages,
    get_website_version_selected_pages_ids,
)
from pages.services import get_page_version_by_guid_or_404
from translations.serializers import TextTranslationSerializer
from commons.decorators.user_decorators import check_user_ownership
from commons.enums import OwnershipType


class PageViewSet(ModelViewSet):
    serializer_class = PageSerializer
    queryset = Page.objects.all()
    http_method_names = ['get', 'post']
    lookup_field = 'guid'

    def get_queryset(self):
        return get_website_version_all_pages(self.kwargs.get('guid'))

    def get_serializer_class(self):
        if self.action == 'import_pages':
            return PageImportSerializer
        if self.action == 'sync_pages':
            return EmptySerializer
        if self.action == 'sync_and_add_pages':
            return EmptySerializer
        return PageSerializer

    def get_serializer_context(self):
        context = super(PageViewSet, self).get_serializer_context()
        website_version_selected_pages_ids = get_website_version_selected_pages_ids(
            self.kwargs.get('guid')
        )
        context.update(
            {
                'website_version_guid': self.kwargs.get('guid'),
                'website_version_selected_pages_ids': website_version_selected_pages_ids,
            }
        )
        return context

    @action(detail=False, methods=['POST'], url_path='import-pages')
    @check_user_ownership(argument=OwnershipType.website_version)
    def import_pages(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[CustomUserRateThrottle],
        url_path='sync-pages',
    )
    @check_user_ownership(argument=OwnershipType.website_version)
    def sync_pages(self, request, guid=None):
        pages = sync_website_pages(website_version_guid=guid)
        serializer = PageSerializer(pages, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['POST'],
        throttle_classes=[CustomUserRateThrottle],
        url_path='sync-and-add-pages',
    )
    @check_user_ownership(argument=OwnershipType.website_version)
    def sync_and_add_pages(self, request, guid=None):
        page_versions = sync_and_add_website_version_pages(website_version_guid=guid)
        read_serializer = PageLangVersionListSerializer(page_versions, many=True)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "POST" not allowed')

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')


class PageVersionListOrCreateViewSet(ModelViewSet):
    serializer_class = PageLangVersionListSerializer
    queryset = PageLangVersion.objects.all()
    lookup_field = 'guid'
    filter_backends = [CustomSearchFilter, CustomOrderingFilter, CustomFilter]
    search_fields = ['page__page_url']
    http_method_names = [
        'get',
        'post',
    ]

    def get_queryset(self):
        return self.queryset.filter(
            website_lang_version__guid=self.kwargs['guid']
        ).select_related()

    def get_serializer_class(self):
        if self.action == 'create':
            return PageLangVersionCreateSerializer
        if self.action in [
            'sync_selected_page_versions',
            'ai_translate_page_versions',
            'sync_links_and_content_of_page_versions',
        ]:
            return PageVersionSyncSerializer
        if self.action == 'publish_selected_page_versions':
            return PageVersionPublishSerializer
        if self.action == 'unpublish_page_versions':
            return PageVersionUnpublishSerializer
        if self.action == 'word_count_page_versions':
            return PageVersionBaseInputSerializer
        return PageLangVersionListSerializer

    def get_serializer_context(self):
        context = super(PageVersionListOrCreateViewSet, self).get_serializer_context()
        context.update({'website_version_guid': self.kwargs.get('guid')})
        return context

    @check_user_ownership(argument=OwnershipType.website_version)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='sync-page-versions')
    def sync_selected_page_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='sync-links-and-content')
    def sync_links_and_content_of_page_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='publish-page-versions')
    def publish_selected_page_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'Published': True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='ai-translate-page-versions')
    def ai_translate_page_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='unpublish-page-versions')
    def unpublish_page_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'Unpublish': True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='word-count')
    def word_count_page_versions(self, request, guid=None):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        page_versions = word_count_of_page_versions(
            website_version_guid=guid,
            page_version_guid_ids=data.get('page_version_guid_ids', []),
            all=data.get('all', False),
        )
        return Response(page_versions, status=status.HTTP_200_OK)

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')


class PageVersionViewSet(ModelViewSet):
    serializer_class = PageLangVersionListSerializer
    queryset = PageLangVersion.objects.all()
    lookup_field = 'guid'
    filter_backends = [SearchFilter]
    search_fields = ['page__page_url']
    http_method_names = ['get', 'put', 'delete', 'post', 'patch']

    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')

    def get_serializer_class(self):
        if self.action in [
            'parse',
            'ai_translate',
            'words_count',
            'export_page_version_translations',
        ]:
            return EmptySerializer
        if self.action in ['publish', 'unpublish']:
            return PageLangVersionPublishSerializer
        if self.action == 'create':
            return PageLangVersionCreateSerializer
        if self.action == 'partial_update':
            return PageLangVersionPatchSerializer
        if self.action == 'ai_translate_selected_page_version_elements':
            return PageVersionElementSerializer
        if self.action == 'import_page_version_translations':
            return PageVersionImportTranslationSerializer
        if self.action == 'add_page_version_custom_code':
            return PageVersionCustomCodeSerializer
        return PageLangVersionListSerializer

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')

    @check_user_ownership(argument=OwnershipType.page_version)
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        read_serializer = PageLangVersionListSerializer(serializer.instance)
        return Response(read_serializer.data, status=status.HTTP_202_ACCEPTED)

    @check_user_ownership(argument=OwnershipType.page_version)
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @check_user_ownership(argument=OwnershipType.page_version)
    def destroy(self, request, guid):
        soft_delete_page_version(guid)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], name='Parse page')
    @check_user_ownership(argument=OwnershipType.page_version)
    def parse(self, request, guid=None):
        page_version = get_page_version_by_guid_or_404(page_guid=guid)
        parsed_page = parse_page(page_guid=page_version.page.guid)
        serializer = ParsedPageSerializer(
            parsed_page, context={'page_version_guid': guid}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], name='Get parsed elements')
    @check_user_ownership(argument=OwnershipType.page_version)
    def elements(self, request, guid=None):
        parsed_page = get_parsed_page_version(page_guid=guid)
        serializer = ParsedPageSerializer(
            parsed_page, context={'page_version_guid': guid}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], name='Words Count')
    @check_user_ownership(argument=OwnershipType.page_version)
    def words_count(self, request, guid=None):
        words = page_version_words_count(page_version_guid=guid)
        return Response({'number_of_words': words}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], name='AI Translate Page')
    @check_user_ownership(argument=OwnershipType.page_version)
    def ai_translate(self, request, guid=None):
        translated_elements = translate_page_version(
            page_version_guid=guid, user=request.user
        )
        serializer = TextTranslationSerializer(translated_elements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], name='Publish page')
    @check_user_ownership(argument=OwnershipType.page_version)
    def publish(self, request, guid=None):
        serializer = PageLangVersionPublishSerializer(data=request.data)
        if serializer.is_valid(True):
            publish_page_version(
                page_guid=guid, website_domain_guid=serializer.data.get('domain_guid')
            )
        return Response({'Published': True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], name='Un Publish Page')
    @check_user_ownership(argument=OwnershipType.page_version)
    def unpublish(self, request, guid=None):
        serializer = PageLangVersionPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unpublished = unpublish_page_version(
            page_version_guid=guid,
            website_domain_guid=serializer.data.get('domain_guid'),
        )
        return Response({'Unpublished': unpublished}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='ai-translate-elements')
    @check_user_ownership(argument=OwnershipType.page_version)
    def ai_translate_selected_page_version_elements(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = TextTranslationSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'], url_path='export-translations')
    def export_page_version_translations(self, request, guid=None):
        csv_content = export_csv_page_version_translations(page_version_guid=guid)
        response = HttpResponse(csv_content, content_type='text/csv')
        response[
            'Content-Disposition'
        ] = f'attachment; filename="{guid}_translations.csv"'
        return response

    @action(
        detail=True,
        methods=['POST'],
        parser_classes=(
            parsers.FormParser,
            parsers.MultiPartParser,
            parsers.FileUploadParser,
        ),
        url_path='import-translations',
    )
    def import_page_version_translations(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = TextTranslationSerializer(serializer.instance, many=True)
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], url_path='custom-code')
    def add_page_version_custom_code(self, request):
        serializer = PageVersionCustomCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
