from rest_framework import serializers
from languages.serializer import LanguageSerializer
from projects.models import (
    IgnoreProjectClass,
    Project,
    ProjectDisableWordTranslation,
    ProjectMedia,
    ProjectPlatform,
)
from languages.models import Language
from projects.services import create_disable_word_translation, create_project
from projects.selectors import get_project_meta_identifier_string
from django.conf import settings
from rest_framework.exceptions import ValidationError
from app.external_services.serve_services import (
    create_or_update_website_in_serve_service,
)
from websites.serializers import WebsiteDomainSerializer
import logging
from projects.dns_config_services import get_project_dns_config


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'guid',
            'name',
            'platform',
            'domain',
            'website_url',
            'content_url',
            'serve_in_www',
            'archived',
            'verified',
            'screenshot',
            'is_disabled',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['main_language'] = LanguageSerializer(instance.main_language).data
        response['ignore_classes'] = IgnoreProjectClassSerializer(
            instance.ignore_project_classes, many=True
        ).data
        website = instance.get_website()
        if website:
            response['domains'] = WebsiteDomainSerializer(
                website.domains.filter(is_deleted=False), many=True
            ).data
        return response


class CustomProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('guid', 'name')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        website = instance.get_website()
        if website:
            response['domains'] = WebsiteDomainSerializer(
                website.domains.filter(is_deleted=False), many=True
            ).data
        return response


class ProjectCreateSerializer(serializers.ModelSerializer):
    language_guid = serializers.SlugRelatedField(
        queryset=Language.objects.all(),
        required=False,
        slug_field='guid',
        source='main_language',
    )

    class Meta:
        model = Project
        fields = ('name', 'platform', 'domain', 'language_guid', 'serve_in_www')

    def create(self, validated_data):
        return create_project(
            validated_data.get('name'),
            validated_data.get('platform', ProjectPlatform.WEBFLOW),
            validated_data.get('domain'),
            validated_data.get('serve_in_www'),
            validated_data.get('created_by_id'),
            validated_data.get('main_language'),
        )


class ProjectMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMedia
        fields = ('media_file',)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['project_guid'] = instance.project.guid
        return response


class IgnoreProjectClassSerializer(serializers.ModelSerializer):
    project_guid = serializers.SlugRelatedField(
        read_only=True,
        required=False,
        slug_field='guid',
        source='project',
    )

    class Meta:
        model = IgnoreProjectClass
        fields = (
            'project_guid',
            'class_name',
        )


class ProjectPatchSerializer(serializers.ModelSerializer):
    language_guid = serializers.SlugRelatedField(
        queryset=Language.objects.all(),
        required=False,
        slug_field='guid',
        source='main_language',
    )

    class Meta:
        model = Project
        fields = ('name', 'serve_in_www', 'domain', 'language_guid', 'platform')

    def update(self, instance, validated_data):
        if instance.verified and validated_data.get('domain') != instance.domain:
            logging.warning(
                f'You cannot change domain of verified project with guid {instance.guid}'
            )
            raise ValidationError('You cannot change domain of verified project!')
        updated_instance = super().update(instance, validated_data)
        website = instance.get_website()
        if website:
            create_or_update_website_in_serve_service(website)
        return updated_instance


class ProjectConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            'guid',
            'domain',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        project_identifier = instance.get_identifier()
        if project_identifier:
            response['meta_identifier'] = get_project_meta_identifier_string(instance)
        response['DNS_RECORDS_SETUP'] = get_project_dns_config(instance)
        response[
            f'{instance.platform}_CUSTOM_DOMAIN'
        ] = f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{instance.domain}'
        response['ENVIRONMENT'] = settings.APP_CONFIG_ENVIRONMENT
        return response


class ProjectDisableWordTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDisableWordTranslation
        fields = ('word',)

    def create(self, validated_data):
        return create_disable_word_translation(
            project_guid=self.context.get('project_guid'),
            word=validated_data.get('word'),
        )
