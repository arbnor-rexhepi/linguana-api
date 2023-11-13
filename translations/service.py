from app.external_services.parser_services import get_text_translation
from translations.models import TextTranslation, TextType, TranslationElementSource
from django.db import transaction
from rest_framework.exceptions import ValidationError, NotFound, APIException
from projects.selectors import get_list_of_words_to_disable_translations
from translations.selectors import (
    get_text_translation_by_guid,
    get_text_translations_of_a_page_version,
    get_text_translations_of_a_website_version,
    get_custom_text_translations_of_a_website_version,
    get_custom_text_translations_of_a_page_version,
)
from commons.utils import clean_string
from django.conf import settings
from app.external_services.cloud_services import translate_text
from users.services import add_user_ai_credits
import logging
from django.db import IntegrityError


def create_or_update_translation(
    page_lang_version,
    text_guid,
    text,
    manual_translation,
    attribute_name,
    parsed_element_type,
    text_type,
    is_media_uploaded,
    source,
):
    try:
        translation = (
            get_text_translation_by_guid(guid=text_guid) if text_guid else None
        )
        if translation:
            translation.manual_translation = manual_translation
            translation.source = source
            translation.text = (
                text if source == TranslationElementSource.CUSTOM else translation.text
            )
            translation.save(
                update_fields=[
                    'text',
                    'manual_translation',
                    'source',
                ]
            )
            return translation

        translation, _ = TextTranslation.objects.update_or_create(
            page_lang_version=page_lang_version,
            text=text,
            attribute_name=attribute_name,
            text_type=text_type,
            defaults={
                'first_translated_on_page_version': page_lang_version,
                'manual_translation': manual_translation,
                'parsed_element_type': parsed_element_type,
                'is_media_uploaded': is_media_uploaded,
                'source': source,
            },
        )
        return translation

    except IntegrityError:
        raise ValidationError(f"This text='{text}' already exist!")

    except Exception as e:
        message = 'Failed to create or update text translation!'
        logging.error(
            f'{message} page_version_guid={page_lang_version.guid}, text={text}. Error:{repr(e)}'
        )
        raise APIException(message)


@transaction.atomic()
def create_or_update_ai_translation(
    page_lang_version,
    text_guid,
    text,
    attribute_name,
    parsed_element_type,
    text_type,
    user,
):
    translation = get_text_translation_by_guid(guid=text_guid) if text_guid else None
    if not translation:
        translation, _ = TextTranslation.objects.get_or_create(
            page_lang_version=page_lang_version,
            text=text,
            attribute_name=attribute_name,
            text_type=text_type,
            defaults={
                'first_translated_on_page_version': page_lang_version,
                'text': text,
                'parsed_element_type': parsed_element_type,
                'text_type': text_type,
            },
        )

    if translation.ai_translation:
        translation.manual_translation = translation.ai_translation
        translation.save()
        return translation

    count_number_of_words_in_text = len(text.split())
    src = page_lang_version.website_lang_version.website.project.main_language.code
    dest = page_lang_version.website_lang_version.language.code

    if settings.USE_GOOGLE_TRANSLATE_FREE_SERVICE:
        response = get_text_translation(text, src, dest)
        if not response:
            raise ValidationError('Translation service is not working right now!')
        translated_text = response.get('translated_text')
    else:
        if count_number_of_words_in_text > user.remaining_credits:
            raise ValidationError('You do not have enough credits.')
        list_of_words = get_list_of_words_to_disable_translations(
            project_id=page_lang_version.website_lang_version.website.project_id
        )
        response = translate_text(text, src, dest, list_of_words)
        translated_text = response.get('translated_text')

    translation.ai_translation = translated_text
    translation.save()

    if not settings.USE_GOOGLE_TRANSLATE_FREE_SERVICE:
        ai_credits_spent = -count_number_of_words_in_text
        add_user_ai_credits(user.id, ai_credits_spent)

    return translation


def get_translations_dict(page_version):
    website_translations = get_text_translations_of_a_website_version(
        page_version.website_lang_version.guid
    )
    page_version_translations = get_text_translations_of_a_page_version(
        page_version.guid
    )
    translation_dict = {}
    for item in website_translations:
        if item.text_type == TextType.ATTRIBUTE:
            translation_dict[clean_string(f'{item.attribute_name}="{item.text}"')] = {
                'guid': item.guid,
                'ai_translation': item.ai_translation,
                'manual_translation': item.manual_translation,
                'translation_services': item.translation_services,
                'from_page': item.page_lang_version.page.page_url,
                'source': item.source,
            }
        else:
            translation_dict[clean_string(item.text)] = {
                'guid': item.guid,
                'ai_translation': item.ai_translation,
                'manual_translation': item.manual_translation,
                'translation_services': item.translation_services,
                'from_page': item.page_lang_version.page.page_url,
                'source': item.source,
            }
    for item in page_version_translations:
        if item.text_type == TextType.ATTRIBUTE:
            translation_dict[clean_string(f'{item.attribute_name}="{item.text}"')] = {
                'guid': item.guid,
                'ai_translation': item.ai_translation,
                'manual_translation': item.manual_translation,
                'translation_services': item.translation_services,
                'from_page': '',
                'source': item.source,
            }
        else:
            translation_dict[clean_string(item.text)] = {
                'guid': item.guid,
                'ai_translation': item.ai_translation,
                'manual_translation': item.manual_translation,
                'translation_services': item.translation_services,
                'from_page': '',
                'source': item.source,
            }

    return translation_dict


def get_custom_translations_dict(page_version):
    website_translations = get_custom_text_translations_of_a_website_version(
        page_version.website_lang_version.guid
    )
    page_version_translations = get_custom_text_translations_of_a_page_version(
        page_version.guid
    )
    translation_dict = {}
    for item in website_translations:
        translation_dict[clean_string(item.text)] = {
            'guid': item.guid,
            'ai_translation': item.ai_translation,
            'manual_translation': item.manual_translation,
            'translation_services': item.translation_services,
            'from_page': item.page_lang_version.page.page_url,
            'source': item.source,
            'date_created': item.date_created,
            'date_updated': item.date_updated,
        }
    for item in page_version_translations:
        translation_dict[clean_string(item.text)] = {
            'guid': item.guid,
            'ai_translation': item.ai_translation,
            'manual_translation': item.manual_translation,
            'translation_services': item.translation_services,
            'from_page': '',
            'source': item.source,
            'date_created': item.date_created,
            'date_updated': item.date_updated,
        }

    return translation_dict


def get_or_create_translation(
    page_lang_version,
    text,
    attribute_name,
    text_type,
    parsed_element_type,
    ai_translation,
):
    return TextTranslation.objects.get_or_create(
        page_lang_version=page_lang_version,
        text=text,
        attribute_name=attribute_name,
        text_type=text_type,
        defaults={
            'first_translated_on_page_version': page_lang_version,
            'text': text,
            'parsed_element_type': parsed_element_type,
            'text_type': text_type,
            'ai_translation': ai_translation,
        },
    )


def get_website_version_text_translations(
    website_version_id, text, attribute_name, text_type
):
    return TextTranslation.objects.filter(
        page_lang_version__website_lang_version_id=website_version_id,
        text=text,
        attribute_name=attribute_name,
        text_type=text_type,
    )


@transaction.atomic()
def apply_all_text_translation(text_translation_guid):
    translation = get_text_translation_by_guid(guid=text_translation_guid)
    if not translation:
        message = f'The translation with guid:{text_translation_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)

    text_translations = get_website_version_text_translations(
        website_version_id=translation.page_lang_version.website_lang_version.id,
        text=translation.text,
        attribute_name=translation.attribute_name,
        text_type=translation.text_type,
    )

    if text_translations:
        text_translations = text_translations.exclude(
            page_lang_version_id=translation.page_lang_version.id
        )
    else:
        return False

    update_translations = text_translations.update(
        ai_translation=translation.ai_translation,
        manual_translation=translation.manual_translation,
    )

    if not update_translations:
        return False
    return True


@transaction.atomic()
def delete_translation(text_translation_guid):
    translation = get_text_translation_by_guid(guid=text_translation_guid)
    if not translation:
        message = f'The translation with guid:{text_translation_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)

    text_translations = get_website_version_text_translations(
        website_version_id=translation.page_lang_version.website_lang_version.id,
        text=translation.text,
        attribute_name=translation.attribute_name,
        text_type=translation.text_type,
    )
    text_translations.hard_delete()
    return True


def create_or_update_text_translation(
    page_lang_version,
    text,
    ai_translation,
    manual_translation,
    text_type,
    attribute_name,
    parsed_element_type,
):
    translation, _ = TextTranslation.objects.update_or_create(
        page_lang_version=page_lang_version,
        text=text,
        attribute_name=attribute_name,
        text_type=text_type,
        defaults={
            'ai_translation': ai_translation,
            'manual_translation': manual_translation,
            'parsed_element_type': parsed_element_type,
        },
    )

    return translation
