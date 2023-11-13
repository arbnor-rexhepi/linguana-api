from rest_framework import serializers
from pages.selectors import get_total_number_of_website_page_versions
from websites.background_services import (
    ai_translate_website_versions,
    publish_website_versions,
    sync_links_and_content_website_versions,
)
from websites.models import Website, WebsiteLangVersion, WebsiteDomain
from websites.services import (
    create_website_versions,
    create_website_domain,
)
from languages.serializer import LanguageSerializer
from app.external_services.serve_services import (
    create_or_update_website_version_in_serve_service,
    create_or_update_website_domain_in_serve_service,
)


class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = (
            'guid',
            'domain',
            'content_url',
            'content_domain_url',
            'original_lang_code',
        )


class WebsiteLangVersionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteLangVersion
        fields = ('guid', 'language', 'subfolder', 'is_disabled')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['language'] = LanguageSerializer(instance.language).data
        response['total_number_of_pages'] = get_total_number_of_website_page_versions(
            instance.id
        )
        return response


class WebsiteLangVersionCreateSerializer(serializers.ModelSerializer):
    language_guid_ids = serializers.ListField(child=serializers.UUIDField())

    class Meta:
        model = WebsiteLangVersion
        fields = ('language_guid_ids',)

    def create(self, validated_data):
        return create_website_versions(
            project_guid=self.context.get('project_guid'),
            language_guid_ids=validated_data.get('language_guid_ids'),
            user_id=self.context.get('request').user.id,
        )


class WebsiteLangVersionBaseSerializer(serializers.Serializer):
    website_version_guid_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )
    all = serializers.BooleanField(default=False)


class WebsiteLangVersionSyncSerializer(WebsiteLangVersionBaseSerializer):
    def create(self, validated_data):
        return sync_links_and_content_website_versions(
            project_guid=self.context.get('project_guid'),
            website_version_guid_ids=validated_data.get('website_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
        )


class WebsiteLangVersionPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteLangVersion
        fields = ('subfolder',)

    def update(self, instance, validated_data):
        updated_instance = super().update(instance, validated_data)
        create_or_update_website_version_in_serve_service([updated_instance])
        return updated_instance


class WebsiteDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteDomain
        fields = ('guid', 'domain', 'serve_in_www', 'verified', 'domain_type')
        read_only_fields = ('guid', 'verified', 'domain_type')

    def create(self, validated_data):
        return create_website_domain(
            project_guid=self.context.get('project_guid'),
            domain=validated_data.get('domain'),
            serve_in_www=validated_data.get('serve_in_www'),
            user_id=self.context.get('request').user.id,
        )


class WebsiteDomainPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteDomain
        fields = ('guid', 'domain', 'serve_in_www', 'verified')
        read_only_fields = ('guid', 'domain', 'verified', 'domain_type')

    def update(self, instance, validated_data):
        updated_instance = super().update(instance, validated_data)
        create_or_update_website_domain_in_serve_service(updated_instance)
        return updated_instance


class WebsiteVersionPublishSerializer(WebsiteLangVersionBaseSerializer):
    domain_guid = serializers.SlugRelatedField(
        queryset=WebsiteDomain.objects.all(),
        required=True,
        slug_field='guid',
        source='domain',
    )

    def create(self, validated_data):
        return publish_website_versions(
            project_guid=self.context.get('project_guid'),
            website_domain_guid=validated_data.get('domain').guid,
            website_version_guid_ids=validated_data.get('website_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
        )


class WebsiteVersionAiTranslateSerializer(WebsiteLangVersionBaseSerializer):
    def create(self, validated_data):
        return ai_translate_website_versions(
            project_guid=self.context.get('project_guid'),
            website_version_guid_ids=validated_data.get('website_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
        )
