from pages.models import PageLangVersion
from rest_framework import serializers
from translations.models import TextTranslation, TranslationElementSource
from translations.service import (
    create_or_update_ai_translation,
    create_or_update_translation,
)


class TextTranslationSerializer(serializers.ModelSerializer):
    page_lang_version_guid = serializers.SlugRelatedField(
        queryset=PageLangVersion.objects.all(),
        required=True,
        slug_field='guid',
        source='page_lang_version',
    )
    first_translated_on_page_version = serializers.SlugRelatedField(
        required=False,
        slug_field='page_url',
        source='page_lang_version.page',
        read_only=True,
    )

    text_guid = serializers.UUIDField(
        source='guid',
        allow_null=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = TextTranslation
        fields = (
            'text_guid',
            'guid',
            'page_lang_version_guid',
            'text',
            'ai_translation',
            'manual_translation',
            'first_translated_on_page_version',
            'attribute_name',
            'parsed_element_type',
            'text_type',
            'is_media_uploaded',
            'source',
        )
        extra_kwargs = {
            'first_translated_on_page_version': {'read_only': True},
            'ai_translation': {'read_only': True},
            'attribute_name': {'write_only': True},
            'parsed_element_type': {'write_only': True},
            'text_type': {'write_only': True},
        }

    def create(self, validated_data):
        translation = create_or_update_translation(
            page_lang_version=validated_data.get('page_lang_version'),
            text_guid=validated_data.get('guid', None),
            text=validated_data.get('text'),
            manual_translation=validated_data.get('manual_translation'),
            attribute_name=validated_data.get('attribute_name'),
            parsed_element_type=validated_data.get('parsed_element_type'),
            text_type=validated_data.get('text_type'),
            is_media_uploaded=validated_data.get('is_media_uploaded'),
            source=validated_data.get('source', TranslationElementSource.PARSER),
        )
        return translation

    def get_unique_together_validators(self):
        return []


class AutomaticTranslationSerializer(serializers.ModelSerializer):
    page_lang_version_guid = serializers.SlugRelatedField(
        queryset=PageLangVersion.objects.all(),
        required=True,
        slug_field='guid',
        source='page_lang_version',
    )
    text_guid = serializers.UUIDField(
        source='guid',
        allow_null=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = TextTranslation
        fields = (
            'text_guid',
            'guid',
            'page_lang_version_guid',
            'text',
            'attribute_name',
            'parsed_element_type',
            'text_type',
            'source',
        )

    def create(self, validated_data):
        translation = create_or_update_ai_translation(
            page_lang_version=validated_data.get('page_lang_version'),
            text_guid=validated_data.get('guid', None),
            text=validated_data.get('text'),
            attribute_name=validated_data.get('attribute_name'),
            parsed_element_type=validated_data.get('parsed_element_type'),
            text_type=validated_data.get('text_type'),
            user=validated_data.get('user'),
        )
        return translation

    def get_unique_together_validators(self):
        return []
