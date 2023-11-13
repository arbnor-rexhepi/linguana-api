import datetime
import logging
from app.external_services.serve_services import (
    create_or_update_website_settings_in_serve,
    create_or_update_website_version_in_serve_service,
    create_or_update_website_in_serve_service,
    create_or_update_website_domain_in_serve_service,
)
from commons.utils import normalize_domain
from languages.services import get_languages
from pages.selectors import get_deleted_website_page_versions
from projects.selectors import get_user_verified_projects
from translations.selectors import get_text_translations_for_website_version
from users.permission_services import (
    check_user_can_create_custom_domains,
    check_user_can_create_website_versions,
)
from websites.models import (
    Website,
    WebsiteLangVersion,
    WebsiteDomain,
    WebsiteDomainType,
    WebsiteSettings,
)
from pages.services import (
    create_website_default_pages,
    filter_website_page_paths,
    get_new_website_page_ids,
    get_text_list_to_translate,
    prepare_and_create_website_version_pages,
    sync_and_add_website_pages,
    word_count,
)
from websites.selectors import (
    get_website_by_project_guid,
    get_website_version_language_ids,
    get_website_version_by_guid_or_404,
    get_website_domain_by_guid_or_404,
    get_verified_website_domains,
    get_project_website_domain,
    get_website_versions_by_guid_ids,
)
from rest_framework.exceptions import ValidationError, NotFound
from django.db import transaction
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.conf import settings
from projects.verification_services import (
    check_and_verify_dns_records,
    check_if_user_setup_project_in_our_subdomain,
)
from payments.models import SubscriptionPlan
from payments.selectors import get_user_subscription
from users.models import UserType
import json


def create_website_with_default_pages(project_id):
    website = create_website(project_id)
    create_or_update_website_in_serve_service(website)
    user = website.project.created_by
    subscription = get_user_subscription(user_id=user.id)
    show_badge = (
        subscription.plan == SubscriptionPlan.FREE and user.type == UserType.FREE
    )
    settings = {'show_badge': show_badge}
    create_or_update_website_settings(website=website, settings=settings)
    create_or_update_website_settings_in_serve(website=website)
    website_domain = create_default_website_subdomain(website)
    create_or_update_website_domain_in_serve_service(website_domain)
    create_website_default_pages(website.id)


def get_website_default_subdomain(website):
    if not settings.LINGUANA_PUBLISH_SUBDOMAIN:
        logging.error('Missing settings.LINGUANA_PUBLISH_SUBDOMAIN!')
        raise ValidationError('Something went wrong, please try again later!')
    subdomain = f'{slugify(website.project.name)}-{get_random_string(3, allowed_chars="0123456789")}.{settings.LINGUANA_PUBLISH_SUBDOMAIN}'  # noqa
    return subdomain


def create_default_website_subdomain(website):
    return WebsiteDomain.objects.create(
        website=website,
        domain=get_website_default_subdomain(website),
        serve_in_www=False,
        verified=True,
        domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN,
    )


def create_website(project_id):
    return Website.objects.create(project_id=project_id)


def create_website_versions(project_guid, language_guid_ids, user_id):
    check_user_can_create_website_versions(user_id, language_guid_ids)
    website = get_website_by_project_guid(project_guid)
    if not website:
        message = f'The project with guid:{project_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)
    if len(language_guid_ids) == 0:
        return
    website_versions_lang_ids = get_website_version_language_ids(website.id)
    languages = get_languages(language_guid_ids)
    new_languages = languages.exclude(id__in=website_versions_lang_ids)
    if not new_languages:
        raise ValidationError('These versions of the website already exist!')
    if website.project.main_language in new_languages:
        raise ValidationError(
            f'Cannot create a website-version with main project language:{website.project.main_language}!'
        )
    return prepare_and_create_website_versions(website.id, new_languages)


def prepare_and_create_website_versions(website_id, languages):
    website_versions = [
        WebsiteLangVersion(
            website_id=website_id,
            language_id=language.id,
            subfolder=language.code,
        )
        for language in languages
    ]
    return bulk_create_website_versions(website_versions)


def sync_website_versions(project_guid, website_version_guid_ids):
    website = get_website_by_project_guid(project_guid)
    if not website:
        message = f'The project with guid:{project_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)
    sync_and_add_website_pages(website)
    website_versions = get_website_versions_by_guid_ids(website_version_guid_ids)
    if len(website_versions) == 0:
        return []
    pages = website.pages.all()
    page_paths = [page.page_url for page in pages]
    filtered_page_paths = filter_website_page_paths(website=website, paths=page_paths)
    pages = pages.filter(page_url__in=filtered_page_paths)
    page_guid_ids = [page.guid for page in pages]
    for version in website_versions:
        new_page_ids = get_new_website_page_ids(version.id, page_guid_ids)
        if len(new_page_ids) == 0:
            continue
        prepare_and_create_website_version_pages(version.id, new_page_ids)
    return website_versions


@transaction.atomic()
def bulk_create_website_versions(website_versions):
    website_versions = WebsiteLangVersion.objects.bulk_create(website_versions)
    create_or_update_website_version_in_serve_service(website_versions)
    return website_versions


def bulk_update_website_versions(website_versions):
    WebsiteLangVersion.objects.bulk_update(website_versions, ['serve_sync_status'])


@transaction.atomic()
def soft_delete_website_version(website_version_guid):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    website_version.delete()
    website_version.pages.all().delete()
    create_or_update_website_version_in_serve_service([website_version])


@transaction.atomic()
def restore_deleted_website_version(website_version):
    version_deleted_at = website_version.deleted_at
    website_version.restore()
    deleted_at = version_deleted_at - datetime.timedelta(minutes=5)
    get_deleted_website_page_versions(website_version.website.id, deleted_at).restore()
    create_or_update_website_version_in_serve_service([website_version])


@transaction.atomic()
def soft_delete_website_domain(guid):
    website_domain = get_website_domain_by_guid_or_404(guid)
    if website_domain.domain_type == WebsiteDomainType.DEFAULT_SUBDOMAIN:
        raise ValidationError('You cannot delete a default assigned subdomain!')
    website_domain.delete()
    create_or_update_website_domain_in_serve_service(website_domain)


@transaction.atomic()
def create_website_domain(project_guid, domain, serve_in_www, user_id):
    check_user_can_create_custom_domains(user_id)
    website = get_website_by_project_guid(project_guid=project_guid)
    if not website:
        logging.error(
            f'Project does not have a website, project guid:{project_guid}, trying to add domain {domain}'
        )
        raise ValidationError('Project is not verified yet!')
    domain = normalize_domain(domain=domain)
    already_verified_domain = get_verified_website_domains(domain=domain)
    if already_verified_domain:
        logging.error(
            f'Trying to add verified domain {domain}, for project {project_guid}'
        )
        raise ValidationError(
            'This domain is already added and verified by someone else, contact support if you think it is a mistake!'
        )
    project_domains = get_project_website_domain(
        project_guid=project_guid, domain=domain
    )
    if project_domains:
        raise ValidationError('This domain is already added to project')

    website_domain = WebsiteDomain.objects.create(
        website=website,
        domain=domain,
        serve_in_www=serve_in_www,
        verified=False,
        domain_type=WebsiteDomainType.CUSTOM_ADDED,
    )
    return website_domain


@transaction.atomic()
def verify_website_domain(website_domain):
    check_and_verify_dns_records(domain=website_domain.domain)
    check_if_user_setup_project_in_our_subdomain(
        domain=website_domain.domain, platform=website_domain.website.project.platform
    )
    project = website_domain.website.project
    project.domain = f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{website_domain.domain}'
    project.save()
    website_domain.verified = True
    website_domain.save()
    create_or_update_website_in_serve_service(website_domain.website)
    create_or_update_website_domain_in_serve_service(website_domain)
    return website_domain


def create_or_update_website_settings(website, settings):
    website_settings, _ = WebsiteSettings.objects.update_or_create(
        website=website, defaults=settings
    )
    return website_settings


def show_website_badge(website):
    website_user = website.project.created_by
    subscription = get_user_subscription(website_user.id)
    if website_user.type in [UserType.LIFETIME_USER, UserType.UNLIMITED]:
        return False
    if not subscription or subscription.plan == SubscriptionPlan.FREE:
        return True
    return False


def create_or_update_multiple_user_website_settings(user_id, show_badge=False):
    try:
        projects = get_user_verified_projects(user_id)
        if len(projects) == 0:
            return
        websites = [project.website for project in projects if project.website]
        if len(websites) == 0:
            return []
        for website in websites:
            try:
                settings = {'show_badge': show_badge}
                create_or_update_website_settings(website, settings)
                create_or_update_website_settings_in_serve(website)
            except Exception as e:
                logging.error(
                    f'Failed to add website settings for domain:{website.project.domain}, for website_guid:{website.guid}! Error:{repr(e)}'  # noqa
                )
    except Exception as e:
        logging.error(
            f'Failed to create or update user website settings! Error:{repr(e)}'  # noqa
        )
        return


def word_count_of_website_versions(project_guid, website_version_guid_ids, all):
    website = get_website_by_project_guid(project_guid=project_guid)
    dict_of_pages = get_text_of_website_pages(website=website)
    website_versions = website.translations.all()
    if not all:
        website_versions = website_versions.filter(guid__in=website_version_guid_ids)

    list_of_website_versions = []
    for website_version in website_versions:
        text_translations = get_text_translations_for_website_version(
            website_version_guid=website_version.guid
        )
        page_versions = website_version.pages.all()
        list_of_untranslated_text = []
        for page_version in page_versions:
            list_of_untranslated_text.extend(dict_of_pages[page_version.page_id])
        text_for_translations = list(
            set(list_of_untranslated_text) - set(text_translations)
        )
        credits = word_count(list_of_words=text_for_translations)
        list_of_website_versions.append(
            {
                'website_version_guid': website_version.guid,
                'website_version_name': website_version.language.name,
                'credits': credits,
            }
        )

    return list_of_website_versions


def get_text_of_website_pages(website):
    dict_pages = {}
    pages = website.pages.all()
    for page in pages:
        elements = json.load(page.parsed_page.parsed_elements_file).get('elements')
        text_for_translations = get_text_list_to_translate(elements=elements)
        dict_pages[page.id] = text_for_translations

    return dict_pages
