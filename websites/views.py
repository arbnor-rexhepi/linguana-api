from rest_framework.viewsets import ModelViewSet
from websites.models import WebsiteLangVersion, WebsiteDomain
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed, NotFound
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from websites.serializers import (
    WebsiteLangVersionBaseSerializer,
    WebsiteLangVersionListSerializer,
    WebsiteLangVersionCreateSerializer,
    WebsiteLangVersionPatchSerializer,
    WebsiteDomainSerializer,
    WebsiteDomainPatchSerializer,
    WebsiteLangVersionSyncSerializer,
    WebsiteVersionAiTranslateSerializer,
    WebsiteVersionPublishSerializer,
)
from websites.services import (
    soft_delete_website_version,
    soft_delete_website_domain,
    verify_website_domain,
    word_count_of_website_versions,
)
from rest_framework.decorators import action
from commons.serializers import EmptySerializer
from commons.decorators.user_decorators import check_user_ownership
from commons.enums import OwnershipType
from rest_framework import filters


class WebsiteVersionListOrCreateViewSet(ModelViewSet):
    serializer_class = WebsiteLangVersionListSerializer
    queryset = WebsiteLangVersion.objects.all()
    lookup_field = 'guid'
    filter_backends = [filters.SearchFilter]
    search_fields = ['language__name', 'language__code', 'subfolder']
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return WebsiteLangVersion.objects.filter(
            website__project__guid=self.kwargs['guid'],
            website__project__created_by_id=self.request.user.id,
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return WebsiteLangVersionCreateSerializer
        if self.action == 'sync_website_versions':
            return WebsiteLangVersionSyncSerializer
        if self.action == 'publish_website_versions':
            return WebsiteVersionPublishSerializer
        if self.action == 'ai_translate_website_versions':
            return WebsiteVersionAiTranslateSerializer
        if self.action == 'word_count_website_versions':
            return WebsiteLangVersionBaseSerializer
        return WebsiteLangVersionListSerializer

    def get_serializer_context(self):
        context = super(
            WebsiteVersionListOrCreateViewSet, self
        ).get_serializer_context()
        context.update({'project_guid': self.kwargs.get('guid')})
        return context

    @check_user_ownership(argument=OwnershipType.project)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = WebsiteLangVersionListSerializer(
            instance=serializer.instance, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @check_user_ownership(argument=OwnershipType.project)
    @action(
        detail=False,
        methods=['POST'],
        name='Sync website versions!',
        url_path='sync-website-versions',
    )
    def sync_website_versions(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = WebsiteLangVersionListSerializer(
            instance=serializer.instance, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')

    @action(detail=False, methods=['POST'], url_path='publish-website-versions')
    def publish_website_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'Published': True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='ai-translate-website-versions')
    def ai_translate_website_versions(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = WebsiteLangVersionListSerializer(
            instance=serializer.instance, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'], url_path='word-count-website-versions')
    def word_count_website_versions(self, request, guid=None):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        website_versions = word_count_of_website_versions(
            project_guid=guid,
            website_version_guid_ids=data.get('website_version_guid_ids', []),
            all=data.get('all', False),
        )
        return Response(website_versions, status=status.HTTP_200_OK)


class WebsiteLangVersionViewSet(ModelViewSet):
    serializer_class = WebsiteLangVersionListSerializer
    queryset = WebsiteLangVersion.objects.all()
    lookup_field = 'guid'
    http_method_names = ['get', 'patch', 'delete']

    def get_queryset(self):
        return self.filter_queryset(self.queryset).filter(
            website__project__created_by_id=self.request.user.id
        )

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return WebsiteLangVersionPatchSerializer
        return WebsiteLangVersionListSerializer

    @check_user_ownership(argument=OwnershipType.website_version)
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        response_serializer = WebsiteLangVersionListSerializer(
            instance=serializer.instance
        )
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)

    @check_user_ownership(argument=OwnershipType.website_version)
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')

    @check_user_ownership(argument=OwnershipType.website_version)
    def destroy(self, request, guid):
        soft_delete_website_version(guid)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebsiteDomainListOrCreateViewSet(ModelViewSet):
    serializer_class = WebsiteDomainSerializer
    queryset = WebsiteDomain.objects.all()
    lookup_field = 'guid'
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return WebsiteDomain.objects.filter(
            website__project__guid=self.kwargs['guid'],
            website__project__created_by_id=self.request.user.id,
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return WebsiteDomainSerializer
        return WebsiteDomainSerializer

    def get_serializer_context(self):
        context = super(WebsiteDomainListOrCreateViewSet, self).get_serializer_context()
        context.update({'project_guid': self.kwargs.get('guid')})
        return context

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')


class WebsiteDomainViewSet(ModelViewSet):
    serializer_class = WebsiteDomainSerializer
    queryset = WebsiteDomain.objects.all()
    lookup_field = 'guid'
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_website_domain_from_queryset_or_404(self, guid):
        project = self.get_queryset().filter(guid=guid).first()
        if not project:
            raise NotFound(f'The project with guid:{guid} does not exist.')
        return project

    @action(detail=True, methods=['POST'], name='Verify website domain!')
    @check_user_ownership(argument=OwnershipType.website_domain)
    def verify(self, request, guid=None):
        website_domain = self.get_website_domain_from_queryset_or_404(guid)
        website_domain = verify_website_domain(website_domain)
        serializer = WebsiteDomainSerializer(website_domain, many=False)
        return Response(serializer.data)

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')

    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "CREATE" not allowed')

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return WebsiteDomainPatchSerializer
        if self.action == 'verify':
            return EmptySerializer
        return WebsiteDomainSerializer

    @check_user_ownership(argument=OwnershipType.website_domain)
    def destroy(self, request, guid):
        soft_delete_website_domain(guid)
        return Response(status=status.HTTP_204_NO_CONTENT)
