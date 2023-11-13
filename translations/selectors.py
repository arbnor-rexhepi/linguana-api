from translations.models import TextTranslation, TranslationElementSource


def get_text_translations_of_a_website_version(website_version_guid):
    return TextTranslation.objects.filter(
        page_lang_version__website_lang_version__guid=website_version_guid
    ).select_related('page_lang_version__page')


def get_custom_text_translations_of_a_website_version(website_version_guid):
    return TextTranslation.objects.filter(
        page_lang_version__website_lang_version__guid=website_version_guid,
        source=TranslationElementSource.CUSTOM,
    ).select_related('page_lang_version__page')


def get_text_translations_of_a_page_version(page_version_guid):
    return TextTranslation.objects.filter(
        page_lang_version__guid=page_version_guid
    ).select_related('page_lang_version__page')


def get_custom_text_translations_of_a_page_version(page_version_guid):
    return TextTranslation.objects.filter(
        page_lang_version__guid=page_version_guid,
        source=TranslationElementSource.CUSTOM,
    ).select_related('page_lang_version__page')


def get_text_translation_by_guid(guid):
    return TextTranslation.objects.filter(guid=guid).first()


def get_text_translations_for_website_version(website_version_guid):
    return TextTranslation.objects.filter(
        page_lang_version__website_lang_version__guid=website_version_guid
    ).values_list('text', flat=True)
