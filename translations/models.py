from django.db import models
from commons.models import BaseModel
from pages.models import PageLangVersion


class TranslationService(models.TextChoices):
    GOOGLE_CLOUD = 'GOOGLE_CLOUD'


class TextType(models.TextChoices):
    TEXT = 'TEXT'
    RICH_TEXT = 'RICH_TEXT'
    ATTRIBUTE = 'ATTRIBUTE'


class TranslationElementSource(models.TextChoices):
    PARSER = 'PARSER'
    CUSTOM = 'CUSTOM'


class TextTranslation(BaseModel):
    page_lang_version = models.ForeignKey(
        PageLangVersion, on_delete=models.CASCADE, related_name='translations'
    )
    text = models.TextField(blank=False, null=False)
    ai_translation = models.TextField(null=True, blank=True)
    manual_translation = models.TextField(null=True, blank=True)
    translation_services = models.CharField(
        max_length=100,
        choices=TranslationService.choices,
        default=TranslationService.GOOGLE_CLOUD,
    )
    first_translated_on_page_version = models.ForeignKey(
        PageLangVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='first_translations',
    )
    text_type = models.CharField(
        max_length=20, choices=TextType.choices, default=TextType.TEXT
    )
    attribute_name = models.CharField(max_length=100, null=True, blank=True)
    parsed_element_type = models.CharField(max_length=100, null=True, blank=True)
    is_media_uploaded = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=TranslationElementSource.choices,
        default=TranslationElementSource.PARSER,
    )

    @property
    def translated_text(self):
        return self.manual_translation or self.ai_translation or None

    @property
    def first_translated_on_page_path(self):
        if self.first_translated_on_page_version != self.page_lang_version:
            return self.first_translated_on_page_version
        return None

    @property
    def page_url(self):
        return self.page_lang_version.live_translated_page_url

    class Meta:
        db_table = 'text_translation'
        unique_together = (
            'page_lang_version',
            'text',
            'attribute_name',
            'text_type',
        )
