from django.contrib import admin
from translations.models import (
    TextTranslation,
)
from commons.admin import BaseModelAdmin


class TextTranslationAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'guid',
        'website_version_guid',
        'page_lang_version',
        'page_url',
        'attribute_name',
        'text_admin_display',
        'manual_translated_text_admin_display',
        'ai_translated_text_admin_display',
        'text_type',
        'manual_translation',
        'parsed_element_type',
        'source',
        'date_created',
        'date_updated',
        'is_deleted',
        'deleted_at',
    ]
    list_filter = (
        'text_type',
        'attribute_name',
        'parsed_element_type',
        'source',
    )
    search_fields = (
        'text',
        'manual_translation',
        'ai_translation',
        'page_lang_version__page__website__project__domain',
    )

    def website_version_guid(self, obj):
        return obj.page_lang_version.website_lang_version.guid

    def text_admin_display(self, obj):
        return obj.text[0:100]

    def manual_translated_text_admin_display(self, obj):
        if obj.manual_translation:
            return obj.manual_translation[0:100]
        return ''

    def ai_translated_text_admin_display(self, obj):
        if obj.ai_translation:
            return obj.ai_translation[0:100]
        return ''


admin.site.register(TextTranslation, TextTranslationAdmin)
