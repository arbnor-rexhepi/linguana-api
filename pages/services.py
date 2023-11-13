import json
from app.external_services.serve_services import (
    create_or_update_page_version_in_serve,
)

from pages.models import (
    Page,
    PageLangVersion,
    PageStatus,
    PageType,
    PageVersionCustomCode,
    ParsedPage,
    PublishedPageStatus,
    PublishedPageVersionStatus,
)
from commons.utils import get_page_path_from_url, clean_string
from rest_framework.exceptions import NotFound, ValidationError, APIException
from django.db import transaction
from django.core.files.base import ContentFile, File
from translations.models import TextType
import logging
from translations.selectors import get_text_translations_for_website_version
from translations.service import (
    get_translations_dict,
    get_or_create_translation,
    get_custom_translations_dict,
)
from app.external_services.cloud_services import translate_text_list
from websites.selectors import (
    get_website_version_by_guid_or_404,
    get_website_domain_by_guid_or_404,
)
from projects.selectors import get_list_of_words_to_disable_translations
from websites.models import WebsiteDomainType
from users.services import add_user_ai_credits
from pages.consts import ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE
from commons.exceptions import CustomValidationError

from app.external_services.parser_services import (
    check_page_url_redirect,
    get_translated_page_content,
    get_website_links,
    get_page_elements,
)
from pages.selectors import (
    get_page_version_by_guid,
    get_page_version_custom_codes,
    get_website_page_ids,
    get_website_page_urls,
    get_website_version_page_ids,
    get_page_by_guid,
)


def get_page_by_guid_or_404(page_guid):
    page = get_page_by_guid(page_guid)
    if not page:
        message = f'The page with guid:{page_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)
    return page


def get_page_version_by_guid_or_404(page_guid):
    page_version = get_page_version_by_guid(page_guid)

    if not page_version:
        message = f'The page-version with guid:{page_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)
    return page_version


def create_website_default_pages(website_id):
    default_pages = [
        Page(page_url=PageType.Home.value, website_id=website_id),
        Page(page_url=PageType.Page404.value, website_id=website_id),
        # Page(page_url=PageType.Sitemap.value, website_id=website_id),
    ]
    return bulk_create_website_pages(default_pages)


def bulk_create_website_pages(pages):
    return Page.objects.bulk_create(pages)


def get_or_create_page(website_id, page_url, nr_words):
    page, _ = Page.objects.get_or_create(
        website_id=website_id,
        page_url=page_url.rstrip('/'),
        defaults={'nr_of_words': nr_words},
    )
    return page


def get_or_create_page_version(website_version_id, page_id):
    page, created = PageLangVersion.objects.get_or_create(
        website_lang_version_id=website_version_id, page_id=page_id
    )
    return page, created


@transaction.atomic()
def create_page_version(website_version_guid, page_path):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    page_url = f'{website_version.website.content_url}/{page_path}'
    page_url_redirect = check_page_url_redirect(page_url)
    if not page_url_redirect:
        message = f'Failed to create page-version from url:{page_url}.'
        logging.error(message)
        raise ValidationError('Page with requested path is not reachable by us!')
    number_words_of_page = 0
    page_path = get_page_path_from_url(page_url_redirect)
    page = get_or_create_page(
        website_version.website.id, page_path, number_words_of_page
    )
    page_version, created = get_or_create_page_version(website_version.id, page.id)
    if not created:
        message = f'The page with path: {page_path} already exist.'
        logging.warning(message)
        raise ValidationError(message)
    logging.info(f'The page with path:{page_path} has been created successfully.')
    return page_version


@transaction.atomic()
def sync_and_add_website_version_pages(website_version_guid):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    website = website_version.website
    sync_and_add_website_pages(website)
    page_paths = [page.page_url for page in website.pages.all()]
    filtered_page_paths = filter_website_page_paths(website, page_paths)
    pages_guid_list = [
        page.guid
        for page in website.pages.all()
        if page.page_url in filtered_page_paths
    ]
    website_version_pages = create_website_version_pages(
        website_version_guid=website_version_guid, page_guid_ids=pages_guid_list
    )
    return website_version_pages


def sync_website_pages(website_version_guid):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    website = website_version.website
    website_pages = sync_and_add_website_pages(website)
    return website_pages


def filter_website_page_paths(website, paths):
    # Returns page paths without language subfolders
    website_versions_subfolders = [
        item.final_subfolder_path for item in website.translations.all()
    ]
    filtered_paths = []
    for path in paths:
        if path in website_versions_subfolders:
            continue
        for subfolder in website_versions_subfolders:
            if path.startswith(f'{subfolder}/'):
                path = path.split(f'{subfolder}/')[-1]
        filtered_paths.append(path)
    return filtered_paths


def check_and_update_page_statuses(website, current_page_paths, new_page_paths):
    unlink_page_paths = list(set(current_page_paths) - set(new_page_paths))
    if len(unlink_page_paths) > 0:
        pages = website.pages.all().filter(page_url__in=unlink_page_paths)
        pages.update(status=PageStatus.LINK_NOT_FOUND)
    pages = website.pages.all().exclude(page_url__in=unlink_page_paths)
    pages.update(status=PageStatus.ACTIVE)


def sync_and_add_website_pages(website):
    website_links = get_website_links(website.content_url)
    if not website_links:
        raise APIException('Syncing of website pages failed, please try again!')
    page_paths = [get_page_path_from_url(page_url) for page_url in website_links]
    page_paths = filter_website_page_paths(website, page_paths)
    current_page_paths = get_website_page_urls(website.id)
    check_and_update_page_statuses(
        website=website,
        current_page_paths=current_page_paths,
        new_page_paths=page_paths,
    )
    new_page_paths = list(set(page_paths) - set(current_page_paths))
    if len(new_page_paths) == 0:
        return []
    new_website_pages = prepare_and_create_website_pages(website, new_page_paths)
    return new_website_pages


def prepare_and_create_website_pages(website, page_urls):
    pages = [
        Page(
            website_id=website.id,
            page_url=page_url,
            nr_of_words=0,
        )
        for page_url in page_urls
    ]
    return bulk_create_website_pages(pages)


def create_website_version_pages(website_version_guid, page_guid_ids):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    new_page_ids = get_new_website_page_ids(website_version.id, page_guid_ids)
    if len(new_page_ids) == 0:
        logging.info(f'All pages are sync for website_version:{website_version_guid}')
        return []
    return prepare_and_create_website_version_pages(website_version.id, new_page_ids)


def get_new_website_page_ids(website_version_id, page_guid_ids):
    page_ids = get_website_page_ids(page_guid_ids)
    page_version_ids = get_website_version_page_ids(website_version_id)
    new_page_ids = page_ids.exclude(id__in=page_version_ids)
    return new_page_ids


def prepare_and_create_website_version_pages(website_version_id, page_ids):
    page_versions = [
        PageLangVersion(website_lang_version_id=website_version_id, page_id=id)
        for id in page_ids
    ]
    return bulk_create_page_versions(page_versions)


def bulk_create_page_versions(page_versions):
    return PageLangVersion.objects.bulk_create(page_versions)


def count_parsed_page_words(data, page_guid):
    try:
        num_words = 0
        for element in data.get('elements'):
            if element.get('element_type') == TextType.TEXT:
                num_words += len(element.get('text').split(' '))
            elif element.get('element_type') == TextType.ATTRIBUTE:
                num_words += len(element.get('attribute_value').split(' '))
            elif element.get('element_type') == TextType.RICH_TEXT:
                num_words += len(element.get('element').split(' '))
        return num_words
    except Exception as E:
        logging.error(
            f'Cannot count words for page version:{page_guid}. Error:{repr(E)}'
        )
        return 0


@transaction.atomic()
def parse_website_pages(pages):
    list_of_pages = []
    update_parsed_pages = []
    create_parsed_pages = []
    platform = pages[0].website.project.platform
    for page in pages:
        page_elements = get_page_elements(url=page.full_content_url, platform=platform)
        if not page_elements:
            continue

        parsed_page = page.get_parsed_page()
        parsed_elements_file = File(
            ContentFile(json.dumps(page_elements).encode('utf-8')),
            name=f'parsed-{str(page.guid)}.json',
        )
        if parsed_page:
            parsed_page.parsed_elements_file = parsed_elements_file
            update_parsed_pages.append(parsed_page)
        else:
            create_parsed_pages.append(
                ParsedPage(page=page, parsed_elements_file=parsed_elements_file)
            )

        num_of_words = count_parsed_page_words(data=page_elements, page_guid=page.guid)
        page.nr_of_words = num_of_words
        list_of_pages.append(page)

    if len(list_of_pages) > 0:
        bulk_update_pages(pages=list_of_pages)

    if len(update_parsed_pages) > 0:
        bulk_update_parsed_pages(parsed_pages=update_parsed_pages)

    if len(create_parsed_pages) > 0:
        bulk_create_parsed_pages(parsed_pages=create_parsed_pages)


def bulk_create_parsed_pages(parsed_pages):
    return ParsedPage.objects.bulk_create(parsed_pages)


def bulk_update_parsed_pages(parsed_pages):
    return ParsedPage.objects.bulk_update(parsed_pages, ['parsed_elements_file'])


def bulk_update_pages(pages):
    return Page.objects.bulk_update(pages, ['nr_of_words'])


def parse_page(page_guid):
    page = get_page_by_guid_or_404(page_guid=page_guid)
    page_full_url = page.full_content_url
    platform = page.website.project.platform
    data = get_page_elements(url=page_full_url, platform=platform)
    if not data:
        message = f'The page with guid:{page_guid} cannot be parsed for the moment!'
        logging.error(message)
        raise APIException(message)
    parsed_page, _ = ParsedPage.objects.update_or_create(
        page=page,
        defaults={
            'parsed_elements_file': File(
                ContentFile(json.dumps(data).encode('utf-8')),
                name=f'parsed-{str(page.guid)}.json',
            )
        },
    )
    num_of_words = count_parsed_page_words(data, page_guid)
    page.nr_of_words = num_of_words
    page.save()
    logging.info(f'The page with guid:{page_guid} parsed successfully!')
    return parsed_page


def get_parsed_page_version(page_guid):
    page_version = get_page_version_by_guid_or_404(page_guid)
    parsed_page = page_version.page.get_parsed_page()
    if parsed_page:
        return parsed_page
    parsed_page = parse_page(page_version.page.guid)
    if not parsed_page:
        message = (
            f'The page with guid:{page_guid} can not parse for now, try later please!'
        )
        logging.warning(message)
        raise NotFound(message)
    return parsed_page


def get_page_parsed_elements(page_guid):
    parsed_page = ParsedPage.objects.filter(page__guid=page_guid).first()
    if not parsed_page:
        parsed_page = parse_page(page_guid=page_guid)
    if not parsed_page:
        logging.error(f'Page with guid {page_guid} is not parsed yet!')
        raise ValidationError(f'Page with guid {page_guid} is not parsed yet!')
    elements = json.load(parsed_page.parsed_elements_file).get('elements')
    return elements


def get_page_custom_translations_as_elements(page_version_guid):
    page_version = get_page_version_by_guid_or_404(page_guid=page_version_guid)
    translation_dict = get_custom_translations_dict(page_version)
    sorted_translation_dict = dict(
        sorted(
            translation_dict.items(),
            key=lambda x: (['date_updated'], x[0]),
            reverse=True,
        )
    )
    elements = []
    for key in sorted_translation_dict.keys():
        elements.append(
            {
                'element': key,
                'element_id': None,
                'sort_id': None,
                'element_type': TextType.RICH_TEXT.value,
                'translation': translation_dict.get(key, None),
            }
        )

    return elements


def get_page_parsed_elements_with_translations(page_guid, page_version_guid):
    page_version = get_page_version_by_guid_or_404(page_guid=page_version_guid)
    # TODO: optimize this
    elements = get_page_parsed_elements(page_guid)
    translation_dict = get_translations_dict(page_version)
    for element in elements:
        if element.get('element_type') == TextType.TEXT:
            element['translation'] = translation_dict.get(
                clean_string(element.get('text', '')), None
            )
        elif element.get('element_type') == TextType.ATTRIBUTE:
            element['translation'] = translation_dict.get(
                clean_string(
                    f'{element.get("attribute")}="{element.get("attribute_value","")}"'
                ),
                None,
            )
        elif element.get('element_type') == TextType.RICH_TEXT:
            element['translation'] = translation_dict.get(
                clean_string(element.get('element')), None
            )
    return elements


def get_page_elements_for_publishing(page_guid, page_version_guid):
    elements = get_page_parsed_elements_with_translations(page_guid, page_version_guid)
    custom_elements = get_page_custom_translations_as_elements(
        page_version_guid=page_version_guid
    )
    elements_for_publishing = []
    for element in elements:
        element_translation = element.get('translation')
        # Don't include non translated elements
        if not element_translation:
            continue
        # Don't include ai translations for src and href
        if (
            element_translation.get('ai_translation')
            and (element.get('attribute') in ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE)
            and not element_translation.get('manual_translation')
        ):
            continue
        # Override ai translation if there is manual translation
        final_translation = element_translation.get(
            'manual_translation', ''
        ) or element_translation.get('ai_translation', '')
        text = ''
        if element.get('element_type') == TextType.TEXT:
            text = element.get('text')
        elif element.get('element_type') == TextType.ATTRIBUTE:
            text = element.get('attribute_value')
        elif element.get('element_type') == TextType.RICH_TEXT:
            text = element.get('element')

        if text and final_translation:
            elements_for_publishing.append(
                {
                    'element_type': element.get('element_type', ''),
                    'text': text,
                    'replacement': final_translation,
                    'attribute_name': element.get('attribute', ''),
                }
            )
    for element in custom_elements:
        element_translation = element.get('translation')
        # Don't include non translated elements
        if not element_translation:
            continue
        # Override ai translation if there is manual translation
        final_translation = element_translation.get(
            'manual_translation', ''
        ) or element_translation.get('ai_translation', '')
        text = element.get('element')
        if text and final_translation:
            elements_for_publishing.append(
                {
                    'element_type': element.get('element_type', ''),
                    'text': text,
                    'replacement': final_translation,
                    'attribute_name': '',
                }
            )

    return elements_for_publishing


# TODO implements bulk publishing in API and serve
def publish_multiple_page_versions(page_versions, website_domain_guid):
    failed_publish_pages = 0
    for page_version in page_versions:
        try:
            publish_page_version(
                page_guid=page_version.guid, website_domain_guid=website_domain_guid
            )
        except:  # noqa
            failed_publish_pages += 1
            continue
    website_version_guid = page_versions[0].website_lang_version.guid
    if len(page_versions) == failed_publish_pages:
        message = f'Failed to publish page versions, website_version_guid:{website_version_guid}.'
        logging.error(message)
        raise ValidationError(message)


def publish_page_version(page_guid, website_domain_guid):
    page_version = get_page_version_by_guid_or_404(page_guid)
    if website_domain_guid:
        website_domain = get_website_domain_by_guid_or_404(guid=website_domain_guid)
        if not website_domain.verified:
            raise ValidationError('You need to verify the domain to publish!')
    # TODO: Publishing on main domain if no website_domain_guid
    # Will be removed after we add selector on frontend
    if not website_domain:
        website_domain = (
            page_version.page.website.domains.filter(
                domain_type=WebsiteDomainType.CUSTOM_ADDED
            ).first()
            or page_version.page.website.domains.filter(
                domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN
            ).first()
        )
    if not website_domain:
        raise ValidationError('You need to publish in any of your verified domains!')
    if website_domain.website.guid != page_version.website_lang_version.website.guid:
        logging.error(
            f'Trying to publish page version guid {page_guid} on website domain guid {website_domain_guid}, not same website!'  # noqa
        )
        raise ValidationError('This domain is not part of this website version!')

    elements = get_page_elements_for_publishing(page_version.page.guid, page_guid)
    custom_codes = get_custom_codes(page_version=page_version)
    content = get_translated_page_content(  # noqa
        page_version.page.full_content_url,
        elements,
        website_domain.website.project.platform,
        custom_codes=custom_codes,
    )

    if not content:
        message = f'The page with guid:{page_guid} is not published, please try again!'
        logging.warning(message)
        page_version.page.status = PageStatus.PAGE_NOT_FOUND
        page_version.page.save()
        raise NotFound(message)

    publish_page_version = create_or_update_page_version_in_serve(
        page_version, content, website_domain_guid=website_domain.guid
    )
    published_page_obj = PublishedPageVersionStatus.objects.create(
        page_version=page_version, domain=website_domain
    )

    if not publish_page_version:
        published_page_obj.failed = True
        published_page_obj.save()
        logging.error(f'The page-version with guid:{page_guid} is not published!')
        raise ValidationError(f'Cannot publish the page with version guid:{page_guid}')

    logging.info(
        f'The page-version with guid:{page_guid} has been published successfully!'
    )
    return publish_page_version


def get_custom_codes(page_version):
    custom_codes = get_page_version_custom_codes(
        project_id=page_version.website_lang_version.website.project.id,
        website_version_id=page_version.website_lang_version.id,
        page_version_id=page_version.id,
    )
    if not custom_codes:
        return []

    return [
        {
            'page_version_guid': page_version.guid,
            'head_code': item.head_code,
            'body_code': item.body_code,
        }
        for item in custom_codes
    ]


def unpublish_page_version(page_version_guid, website_domain_guid):
    page_version = get_page_version_by_guid_or_404(page_version_guid)
    website_domain = get_website_domain_by_guid_or_404(guid=website_domain_guid)
    if website_domain.website.guid != page_version.website_lang_version.website.guid:
        message = f'This domain with guid: {website_domain_guid} is not part of this page versions!'
        logging.error(message)
        raise ValidationError(message)

    published_page_versions_status = (
        page_version.published_pages.filter(
            domain__guid=website_domain_guid,
            failed=False,
            status=PublishedPageStatus.PUBLISHED,
        )
        .order_by('-date_created')
        .first()
    )

    if not published_page_versions_status:
        raise NotFound('This page version does not have any published status!')

    unpublished_page_version = create_or_update_page_version_in_serve(
        page_version=page_version,
        html_content='',
        website_domain_guid=website_domain.guid,
        is_deleted=True,
    )

    if not unpublished_page_version:
        published_page_versions_status.status = PublishedPageStatus.UNPUBLISHED
        published_page_versions_status.failed = True
        published_page_versions_status.save()
        message = f'The page with guid:{page_version_guid} cannot be unpublished for the moment, try again later!'
        logging.error(message)
        raise ValidationError(message)
    published_page_versions_status.status = PublishedPageStatus.UNPUBLISHED
    published_page_versions_status.save()
    return True


def filter_page_version_elements(elements, element_ids):
    return list(filter(lambda element: element['element_id'] in element_ids, elements))


def get_page_version_text_list_to_translate(
    page_guid, page_version_guid, element_ids=[]
):
    # TODO: this will return only no translated texts, add optional parameter
    elements = get_page_parsed_elements_with_translations(page_guid, page_version_guid)
    if element_ids:
        elements = filter_page_version_elements(elements, element_ids)
    text_list_to_translate = get_text_list_to_translate(elements=elements)
    return text_list_to_translate


def get_text_list_to_translate(elements):
    text_list_to_translate = []
    for element in elements:
        if (
            element.get('translation')
            or element.get('media_type')
            or (element.get('attribute') in ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE)
        ):
            continue
        if element.get('element_type') == TextType.TEXT:
            text_list_to_translate.append(element.get('text'))
        elif element.get('element_type') == TextType.ATTRIBUTE:
            text_list_to_translate.append(element.get('attribute_value'))
        elif element.get('element_type') == TextType.RICH_TEXT:
            text_list_to_translate.append(element.get('element'))
    return text_list_to_translate


def page_version_words_count(page_version_guid):
    # TODO: this will count only not translated texts, add optional argument
    page_version = get_page_version_by_guid_or_404(page_version_guid)
    text_list_to_translate = get_page_version_text_list_to_translate(
        page_version.page.guid, page_version_guid
    )
    result = 0
    for text in text_list_to_translate:
        result += len(text.split())
    return result


def word_count_of_page_versions(website_version_guid, page_version_guid_ids, all):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    page_versions = website_version.pages.all()
    if not all:
        page_versions = page_versions.filter(guid__in=page_version_guid_ids)

    text_translations = get_text_translations_for_website_version(
        website_version_guid=website_version_guid
    )

    list_of_untranslated_text = []
    list_of_page_versions = []

    for page_version in page_versions:
        elements = json.load(page_version.page.parsed_page.parsed_elements_file).get(
            'elements'
        )
        nr_of_untranslated_words = 0
        credits = 0
        if elements:
            text_list_to_translate = get_text_list_to_translate(elements=elements)
            list_of_text_for_translations = list(
                set(text_list_to_translate) - set(text_translations)
            )
            nr_of_untranslated_words = word_count(
                list_of_words=list_of_text_for_translations
            )
            list_of_common_words = list(
                set(list_of_text_for_translations).intersection(
                    set(list_of_untranslated_text)
                )
            )
            if len(list_of_common_words) == 0:
                credits = nr_of_untranslated_words
            else:
                credits = nr_of_untranslated_words - word_count(
                    list_of_words=list_of_common_words
                )
        list_of_page_versions.append(
            {
                'page_version_guid': page_version.guid,
                'page': page_version.page.page_url,
                'nr_of_words': nr_of_untranslated_words,
                'credits': credits,
            }
        )
        list_of_untranslated_text.extend(list_of_text_for_translations)

    return list_of_page_versions


def word_count(list_of_words):
    nr_of_words = 0
    for text in list_of_words:
        nr_of_words += len(text.split())
    return nr_of_words


# TODO implements bulk translate in API and serve
def translate_multiple_page_versions(page_versions, user):
    failed_translate_pages = 0
    for page_version in page_versions:
        try:
            translate_page_version(page_version_guid=page_version.guid, user=user)
        except Exception as e:
            if isinstance(e, CustomValidationError):
                continue
            failed_translate_pages += 1
            continue
    website_version_guid = page_versions[0].website_lang_version.guid
    if len(page_versions) == failed_translate_pages:
        message = f'Failed to translate page versions, website_version_guid:{website_version_guid}.'
        logging.error(message)
        raise ValidationError(message)


@transaction.atomic()
def translate_page_version(page_version_guid, user, element_ids=[]):
    # TODO: this will translate only not translated texts
    # TODO: improve if possible
    page_version = get_page_version_by_guid_or_404(page_version_guid)
    elements = get_page_parsed_elements(page_version.page.guid)
    if element_ids:
        elements = filter_page_version_elements(elements, element_ids)
    text_list_to_translate = get_page_version_text_list_to_translate(
        page_version.page.guid, page_version_guid, element_ids
    )
    number_of_words_to_translate = 0
    for text in text_list_to_translate:
        number_of_words_to_translate += len(text.split())
    if number_of_words_to_translate > user.remaining_credits:
        logging.warning(
            f'User with email:{user.email} does not have enough credits to translate page version with guid:{page_version_guid}'  # noqa
        )
        raise ValidationError('You do not have enough credits.')
    if not text_list_to_translate:
        message = f'Page version with guid: {page_version_guid} is already with elements translated!'
        logging.warning(message)
        raise CustomValidationError(message, 'translated_page')
    src = (
        page_version.website_lang_version.website.project.main_language.ai_translation_code
    )
    dest = page_version.website_lang_version.language.ai_translation_code
    list_of_words = get_list_of_words_to_disable_translations(
        project_id=page_version.website_lang_version.website.project_id
    )
    translations_dict = {}
    translations_list = translate_text_list(
        text_list_to_translate, src, dest, list_of_words
    )
    for t in translations_list:
        translations_dict[clean_string(t.get('input'))] = t.get('translatedText')
    translations_objects = []
    for element in elements:
        if (
            element.get('translation')
            or element.get('media_type')
            or (element.get('attribute') in ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE)
        ):
            continue
        if element.get('element_type') == TextType.TEXT:
            text = element.get('text')
            if translations_dict.get(clean_string(text)):
                translation, _ = get_or_create_translation(
                    page_version,
                    text,
                    '',
                    TextType.TEXT,
                    element.get('element_name'),
                    translations_dict.get(clean_string(text)),
                )
                translations_objects.append(translation)
        elif element.get('element_type') == TextType.ATTRIBUTE:
            text = element.get('attribute_value')
            if translations_dict.get(clean_string(text)):
                translation, _ = get_or_create_translation(
                    page_version,
                    text,
                    element.get('attribute'),
                    TextType.ATTRIBUTE,
                    element.get('element_name'),
                    translations_dict.get(clean_string(text)),
                )
                translations_objects.append(translation)
        elif element.get('element_type') == TextType.RICH_TEXT:
            text = element.get('element')
            if translations_dict.get(clean_string(text)):
                translation, _ = get_or_create_translation(
                    page_version,
                    text,
                    '',
                    TextType.RICH_TEXT,
                    element.get('element_name'),
                    translations_dict.get(clean_string(text)),
                )
                translations_objects.append(translation)
    add_user_ai_credits(user.id, -number_of_words_to_translate)
    return translations_objects


@transaction.atomic()
def soft_delete_page_version(page_version_guid):
    page_version = get_page_version_by_guid_or_404(page_version_guid)
    page_version.delete()
    published_domain_guids = [
        item.domain.guid for item in page_version.published_pages.all()
    ]
    for domain in published_domain_guids:
        create_or_update_page_version_in_serve(
            page_version, html_content='', is_deleted=True, website_domain_guid=domain
        )


def ai_translate_selected_page_version_elements(page_version_guid, user, element_ids):
    if len(element_ids) == 0:
        return []
    translated_elements = translate_page_version(page_version_guid, user, element_ids)
    return translated_elements


def create_page_version_custom_code(
    project, website_version, page_version, head_code, body_code
):
    if not any((project, website_version, page_version)):
        raise ValidationError(
            'You must assign custom code to at least one entity ex: project, language or page!'
        )

    return PageVersionCustomCode.objects.create(
        project=project,
        website_version=website_version,
        page_version=page_version,
        head_code=head_code,
        body_code=body_code,
    )
