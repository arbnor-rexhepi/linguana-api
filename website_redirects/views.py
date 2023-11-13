from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from website_redirects.serializers import (
    WebsiteRedirectSerializer,
)
from website_redirects.services import (
    get_website_redirects,
    create_website_redirect,
    update_website_redirect,
    get_website_redirect,
    delete_website_redirect,
)
from rest_framework.exceptions import MethodNotAllowed


class WebsiteRedirectListAndCreateViewSet(ModelViewSet):
    serializer_class = WebsiteRedirectSerializer
    queryset = None
    lookup_field = 'guid'
    http_method_names = ['get', 'post']

    def list(self, request, guid=None):
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        redirects = get_website_redirects(project_guid=guid, limit=limit, offset=offset)
        return Response(redirects, status=status.HTTP_200_OK)

    def create(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        redirect = create_website_redirect(project_guid=guid, data=serializer.data)
        return Response(redirect, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(auto_schema=None)
    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(detail='Method "GET" not allowed')


class WebsiteRedirectViewSet(ModelViewSet):
    serializer_class = WebsiteRedirectSerializer
    queryset = None
    lookup_field = 'guid'
    http_method_names = ['get', 'put', 'delete']

    @swagger_auto_schema(auto_schema=None)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def update(self, request, guid=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        redirect = update_website_redirect(
            website_redirect_guid=guid, data=serializer.data
        )
        return Response(redirect, status=status.HTTP_200_OK)

    def retrieve(self, request, guid=None):
        redirect = get_website_redirect(website_redirect_guid=guid)
        return Response(redirect, status=status.HTTP_200_OK)

    def destroy(self, request, guid=None):
        delete_website_redirect(website_redirect_guid=guid)
        return Response(status=status.HTTP_204_NO_CONTENT)
