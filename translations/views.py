from rest_framework.viewsets import ModelViewSet
from commons.serializers import EmptySerializer
from translations.models import TextTranslation
from translations.serializers import (
    AutomaticTranslationSerializer,
    TextTranslationSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from translations.service import apply_all_text_translation, delete_translation


class TextTranslationViewSet(ModelViewSet):
    serializer_class = TextTranslationSerializer
    queryset = TextTranslation.objects.all()
    lookup_field = 'guid'
    http_method_names = ['post']

    def get_serializer_class(self):
        if self.action == 'ai_translate':
            return AutomaticTranslationSerializer
        if self.action == 'apply_all_translation':
            return EmptySerializer
        if self.action == 'delete_translation':
            return EmptySerializer
        return TextTranslationSerializer

    @action(detail=False, methods=['POST'], name='Translate Page Element')
    def ai_translate(self, request):
        serializer = AutomaticTranslationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            translation = serializer.save(user=request.user)
        response_serializer = TextTranslationSerializer(translation)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST'],
        name='Apply translation to all pages',
        url_path='apply-all',
    )
    def apply_all_translation(self, request, guid=None):
        is_applied_translation = apply_all_text_translation(text_translation_guid=guid)
        return Response(
            {'is_applied': is_applied_translation}, status=status.HTTP_200_OK
        )

    # TODO change method type to DELETE
    # delete this obj in response {'deleted': is_deleted} and
    # change status response to 204
    @action(
        detail=True,
        methods=['POST'],
        name='Delete translation',
        url_path='delete',
    )
    def delete_translation(self, request, guid=None):
        is_deleted = delete_translation(text_translation_guid=guid)
        return Response({'deleted': is_deleted}, status=status.HTTP_200_OK)
