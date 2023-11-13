from rest_framework.viewsets import ModelViewSet
from app.external_services.serve_sync_services import sync_project
from commons.serializers import EmptySerializer
from projects.models import Project, ProjectDisableWordTranslation
from projects.serializers import (
    IgnoreProjectClassSerializer,
    ProjectDisableWordTranslationSerializer,
    ProjectMediaSerializer,
    ProjectSerializer,
    ProjectCreateSerializer,
    ProjectConfigSerializer,
    ProjectPatchSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters, status, parsers
from rest_framework.decorators import APIView
from rest_framework.permissions import AllowAny
from commons.utils import normalize_domain
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import ListCreateAPIView
from projects.services import (
    delete_ignore_project_class,
    file_upload,
    create_ignore_project_class,
    generate_and_save_project_screenshot,
    soft_delete_project,
    verify_project_domain_ownership,
    allow_ssl_for_domain,
)


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    lookup_field = 'guid'
    http_method_names = ['get', 'patch', 'post', 'delete']

    def get_serializer_class(self):
        if self.action == 'file_upload':
            return ProjectMediaSerializer
        if self.action == 'sync_objects':
            return EmptySerializer
        if self.action == 'run_scripts':
            return EmptySerializer
        if self.action == 'config':
            return EmptySerializer
        if self.action == 'create':
            return ProjectCreateSerializer
        if self.action == 'verify':
            return EmptySerializer
        if self.action == 'create_ignore_class':
            return IgnoreProjectClassSerializer
        if self.action == 'partial_update':
            return ProjectPatchSerializer
        return ProjectSerializer

    def get_queryset(self):
        return self.queryset.filter(created_by_id=self.request.user.id)

    def get_project_from_queryset_or_404(self, guid):
        project = self.get_queryset().filter(guid=guid).first()
        if not project:
            raise NotFound(f'The project with guid:{guid} does not exist.')
        return project

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        generate_and_save_project_screenshot(serializer.instance)
        response_serializer = ProjectSerializer(instance=serializer.instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(created_by_id=self.request.user.id)

    def destroy(self, request, guid):
        project = self.get_project_from_queryset_or_404(guid)
        soft_delete_project(project)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['PUT'], name='archive or unarchive project')
    def archive(self, request, guid):
        project = self.get_project_from_queryset_or_404(guid)
        project.archived = True
        project.save()
        serializer = self.get_serializer(project, many=False)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'], name='Verify site ownership!')
    def verify(self, request, guid=None):
        project = self.get_project_from_queryset_or_404(guid)
        project = verify_project_domain_ownership(project)
        serializer = ProjectSerializer(project, many=False)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'], name='Sync project objects between services')
    def sync_objects(self, request, guid=None):
        if not request.user.is_superuser:
            raise PermissionDenied('You cannot run scripts')
        project = Project.global_objects.filter(guid=guid).first()
        sync_project(project)
        return Response({'Finished syncing': True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['GET'], name='Get project config!')
    def config(self, request, guid=None):
        project = self.get_project_from_queryset_or_404(guid)
        serializer = ProjectConfigSerializer(project)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def run_scripts(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied('You cannot run scripts')
        from projects.scripts.screenshots import sync_generate_project_screenshots
        from projects.scripts.website_settings import create_or_update_website_settings

        sync_generate_project_screenshots()
        create_or_update_website_settings()
        return Response('Finished')

    @action(
        detail=True,
        methods=['POST'],
        parser_classes=(
            parsers.FormParser,
            parsers.MultiPartParser,
            parsers.FileUploadParser,
        ),
        name='file upload',
        url_path='file-upload',
    )
    def file_upload(
        self,
        request,
        guid=None,
    ):
        file = self.request.FILES.get('media_file')
        project_media = file_upload(project_guid=guid, media_file=file)
        serializer = ProjectMediaSerializer(project_media)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'], url_path='create-ignore-class')
    def create_ignore_class(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        class_name = serializer.data.get('class_name')
        ignore_project_class = create_ignore_project_class(
            project_guid=guid, class_name=class_name
        )
        read_serializer = self.get_serializer(ignore_project_class)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['DELETE'],
        url_path='delete-ignore-class/(?P<class_name>[^/.]+)',
    )
    def delete_ignore_class(self, request, class_name, guid=None):
        delete_ignore_project_class(project_guid=guid, class_name=class_name)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DomainCheck(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        domain_to_check = normalize_domain(request.GET.get('domain', ''))
        if not domain_to_check:
            return Response('Domain is not allowed', 400)
        allow = allow_ssl_for_domain(domain_to_check)
        if allow:
            return Response('Domain is allowed', status=200)
        return Response('Domain is not allowed', 400)


class ProjectDisableTranslationView(ListCreateAPIView):
    queryset = ProjectDisableWordTranslation.objects.all()
    serializer_class = ProjectDisableWordTranslationSerializer
    http_method_names = ['get', 'post']
    lookup_field = 'guid'

    def get_queryset(self):
        return self.queryset.filter(project__guid=self.kwargs['guid']).select_related(
            'project'
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'project_guid': self.kwargs.get('guid')})
        return context
