from pages.import_export_services import import_csv_page_version_translations
from pages.models import (
    Page,
    PageVersionCustomCode,
    PageLangVersion,
    ParsedPage,
    PublishedPageVersionStatus,
)
from rest_framework import serializers
from pages.services import (
    ai_translate_selected_page_version_elements,
    create_page_version_custom_code,
    create_page_version,
    create_website_version_pages,
    get_page_parsed_elements_with_translations,
    get_page_custom_translations_as_elements,
)
from pages.background_services import (
    publish_selected_website_version_pages,
    sync_or_ai_translate_selected_website_version_pages,
    unpublish_page_versions,
)
from projects.models import Project
from websites.models import Website, WebsiteLangVersion, WebsiteDomain
from projects.serializers import CustomProjectSerializer


class PageSerializer(serializers.ModelSerializer):
    website_guid = serializers.SlugRelatedField(
        queryset=Website.objects.all(),
        required=True,
        slug_field='guid',
        source='website',
    )

    class Meta:
        model = Page
        fields = (
            'guid',
            'full_content_url',
            'full_url',
            'page_url',
            'website_guid',
            'display_name',
            'nr_of_words',
            'status',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['is_selected'] = instance.id in list(
            self.context.get('website_version_selected_pages_ids', [])
        )
        return response


class PageImportSerializer(serializers.ModelSerializer):
    page_guid_ids = serializers.ListField(child=serializers.UUIDField())

    class Meta:
        model = Page
        fields = ('page_guid_ids',)

    def create(self, validated_data):
        return create_website_version_pages(
            self.context.get('website_version_guid'),
            validated_data.get('page_guid_ids'),
        )


class PublishedPageSerializer(serializers.ModelSerializer):
    domain = serializers.SlugRelatedField(
        queryset=WebsiteDomain.objects.all(),
        required=True,
        slug_field='domain',
    )
    domain_type = serializers.CharField(source='domain.domain_type')

    class Meta:
        model = PublishedPageVersionStatus
        fields = ('published_at', 'domain', 'domain_type', 'guid', 'status')


class PageLangVersionListSerializer(serializers.ModelSerializer):
    website_lang_version_guid = serializers.SlugRelatedField(
        queryset=WebsiteLangVersion.objects.all(),
        required=True,
        slug_field='guid',
        source='website_lang_version',
    )
    page_guid = serializers.SlugRelatedField(
        queryset=Page.objects.all(), required=True, slug_field='guid', source='page'
    )

    class Meta:
        model = PageLangVersion
        fields = (
            'guid',
            'website_lang_version_guid',
            'page_guid',
            'custom_page_url',
            'live_translated_page_url',
            'translated_page_path',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['page'] = PageSerializer(instance.page).data
        response['project'] = CustomProjectSerializer(
            instance.website_lang_version.website.project
        ).data

        response['published'] = PublishedPageSerializer(
            instance.published_pages.filter(
                failed=False,
            )
            .order_by('domain', '-date_created')
            .distinct('domain'),
            many=True,
        ).data
        return response


class PageLangVersionCreateSerializer(serializers.ModelSerializer):
    page_path = serializers.CharField(allow_blank=True)

    class Meta:
        model = PageLangVersion
        fields = ('page_path',)

    def create(self, validated_data):
        return create_page_version(
            self.context.get('website_version_guid'),
            validated_data.get('page_path'),
        )


class PageLangVersionPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageLangVersion
        fields = ('custom_page_url',)


class ParsedPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParsedPage
        fields = (
            'guid',
            'date_created',
            'date_updated',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['elements'] = get_page_parsed_elements_with_translations(
            instance.page.guid, page_version_guid=self.context.get('page_version_guid')
        )
        response['custom_elements'] = get_page_custom_translations_as_elements(
            page_version_guid=self.context.get('page_version_guid')
        )
        return response


class PageLangVersionPublishSerializer(serializers.ModelSerializer):
    domain_guid = serializers.SlugRelatedField(
        queryset=WebsiteDomain.objects.filter(),
        required=False,
        slug_field='guid',
        source='domain',
    )

    class Meta:
        model = PublishedPageVersionStatus
        fields = ('domain_guid',)


class PageVersionBaseInputSerializer(serializers.Serializer):
    page_version_guid_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
    )
    all = serializers.BooleanField(default=False)


class PageVersionSyncSerializer(PageVersionBaseInputSerializer):
    def create(self, validated_data):
        return sync_or_ai_translate_selected_website_version_pages(
            website_version_guid=self.context.get('website_version_guid'),
            page_version_guid_ids=validated_data.get('page_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
            view_action_name=self.context.get('view').action,
        )


class PageVersionPublishSerializer(PageVersionBaseInputSerializer):
    domain_guid = serializers.SlugRelatedField(
        queryset=WebsiteDomain.objects.all(),
        required=True,
        slug_field='guid',
        source='domain',
    )

    def create(self, validated_data):
        return publish_selected_website_version_pages(
            website_version_guid=self.context.get('website_version_guid'),
            website_domain_guid=validated_data.get('domain').guid,
            page_version_guid_ids=validated_data.get('page_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
        )


class PageVersionUnpublishSerializer(PageVersionBaseInputSerializer):
    domain_guid = serializers.SlugRelatedField(
        queryset=WebsiteDomain.objects.all(),
        required=True,
        slug_field='guid',
        source='domain',
    )

    def create(self, validated_data):
        return unpublish_page_versions(
            website_version_guid=self.context.get('website_version_guid'),
            website_domain_guid=validated_data.get('domain').guid,
            page_version_guid_ids=validated_data.get('page_version_guid_ids'),
            user=self.context.get('request').user,
            all=validated_data.get('all'),
        )


class PageVersionElementSerializer(serializers.Serializer):
    element_ids = serializers.ListField(child=serializers.IntegerField(default=1))

    class Meta:
        fields = ('element_ids',)

    def create(self, validated_data):
        return ai_translate_selected_page_version_elements(
            page_version_guid=self.context.get('view').kwargs.get('guid'),
            user=self.context.get('request').user,
            element_ids=validated_data.get('element_ids'),
        )


class PageVersionImportTranslationSerializer(serializers.Serializer):
    file = serializers.FileField()

    class Meta:
        fields = ('file',)

    def create(self, validated_data):
        return import_csv_page_version_translations(
            page_version_guid=self.context.get('view').kwargs.get('guid'),
            file=validated_data.get('file'),
        )


class PageVersionCustomCodeSerializer(serializers.ModelSerializer):
    project_guid = serializers.SlugRelatedField(
        allow_null=True,
        required=False,
        queryset=Project.objects.all(),
        slug_field='guid',
        source='project',
    )

    website_version_guid = serializers.SlugRelatedField(
        queryset=WebsiteLangVersion.objects.all(),
        slug_field='guid',
        allow_null=True,
        required=False,
        source='website_version',
    )

    page_version_guid = serializers.SlugRelatedField(
        queryset=PageLangVersion.objects.all(),
        slug_field='guid',
        allow_null=True,
        required=False,
        source='page_version',
    )

    class Meta:
        model = PageVersionCustomCode
        fields = (
            'project_guid',
            'website_version_guid',
            'page_version_guid',
            'head_code',
            'body_code',
        )

    def create(self, validated_data):
        return create_page_version_custom_code(
            project=validated_data.get('project', None),
            website_version=validated_data.get('website_version', None),
            page_version=validated_data.get('page_version', None),
            head_code=validated_data.get('head_code', ''),
            body_code=validated_data.get('body_code', ''),
        )
