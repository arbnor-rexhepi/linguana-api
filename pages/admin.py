from django.contrib import admin
from pages.models import Page, PageLangVersion, ParsedPage, PublishedPageVersionStatus
from commons.admin import BaseModelAdmin
from pages.admin_services import (
    get_elements_for_publishing,
    get_elements_with_translations,
    download_html_translated_page,
    get_parsed_content,
)


class PageAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'website',
        'page_url',
        'full_url',
        'date_created',
        'date_updated',
        'is_deleted',
        'status',
    )
    search_fields = ('page_url', 'website__project__domain')


admin.site.register(Page, PageAdmin)


class ParsedPageAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'page',
        'page_full_url',
        'parsed_elements_file',
        'date_created',
        'date_updated',
        'is_deleted',
    )

    def page_full_url(self, obj):
        return obj.page.full_url


admin.site.register(ParsedPage, ParsedPageAdmin)


class PageLangVersionAdmin(BaseModelAdmin):
    search_fields = (
        'website_lang_version__website__project__domain',
        'guid',
        'page__page_url',
        'page__guid',
        'custom_page_url',
    )
    list_display = (
        'id',
        'guid',
        'website_lang_version',
        'website_lang_version_guid',
        'page',
        'custom_page_url',
        'page_path',
        'date_created',
        'date_updated',
        'is_deleted',
    )

    actions = [
        get_elements_with_translations,
        get_elements_for_publishing,
        download_html_translated_page,
        get_parsed_content,
    ]

    def page_guid(self, obj):
        return obj.page.guid

    def website_lang_version_guid(self, obj):
        return obj.website_lang_version.guid

    def page_path(self, obj):
        return obj.page.page_url


admin.site.register(PageLangVersion, PageLangVersionAdmin)


class PublishedPageVersionStatusAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'domain',
        'page_version',
        'page_version_url',
        'failed',
        'date_created',
        'date_updated',
        'is_deleted',
        'deleted_at',
    )

    list_filter = ('is_deleted', 'failed')
    search_fields = (
        'domain__domain',
        'page_version__guid',
        'page_version__page__website__project__domain',
    )

    def page_version_url(self, obj):
        return obj.page_version.live_translated_page_url


admin.site.register(PublishedPageVersionStatus, PublishedPageVersionStatusAdmin)
