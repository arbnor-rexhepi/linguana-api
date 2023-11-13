import datetime
import logging
from app.external_services.background_services import generate_project_screenshot_async
from app.external_services.serve_services import (
    create_or_update_website_in_serve_service,
)
from pages.selectors import (
    get_deleted_website_page_versions,
    get_all_website_page_versions,
    get_deleted_website_pages,
)
from payments.models import SubscriptionPlan
from projects.models import (
    Project,
    ProjectDisableWordTranslation,
    ProjectMedia,
    IgnoreProjectClass,
    ProjectVerificationIdentifier,
)
from django.db import transaction
from projects.selectors import (
    get_ignore_project_class,
    get_project_by_guid,
    get_user_disabled_projects,
    get_verified_project_by_domain,
)
from users.permission_services import check_user_can_create_project
from websites.selectors import get_deleted_website_domains, get_deleted_website_versions
from websites.services import (
    create_website_with_default_pages,
    get_verified_website_domains,
)
from rest_framework.exceptions import ValidationError, NotFound, APIException
from django.conf import settings
from commons.utils import normalize_domain, check_www
from django.utils.crypto import get_random_string
from projects.verification_services import (
    check_and_verify_meta_tag,
    get_final_url,
    check_and_verify_platform,
)
import re
from django.db import IntegrityError


@transaction.atomic()
def create_project(name, platform, domain, serve_in_www, user_id, main_language):
    check_user_can_create_project(user_id)
    # This will check redirection, and we save final url
    final_url = get_final_url(domain)
    serve_in_www = check_www(final_url)
    # Will remove scheme, www and path
    domain = normalize_domain(final_url)
    project = get_verified_project_by_domain(domain)
    if project:
        message = f'There is already a verified project with the domain:{domain}!'
        logging.error(message)
        raise ValidationError(message)
    project = Project.objects.create(
        name=name,
        domain=domain,
        platform=platform,
        created_by_id=user_id,
        main_language=main_language,
        serve_in_www=serve_in_www,
    )
    ProjectVerificationIdentifier.objects.create(
        project=project, identifier=get_random_string(20)
    )
    logging.info(f'The project with domain:{domain} has been created successfully!')
    return project


def generate_and_save_project_screenshot(project):
    if settings.AWS_TAKE_SCREENSHOT_LAMBDA:
        generate_project_screenshot_async(project)


def get_project_by_guid_or_404(project_guid):
    project = get_project_by_guid(project_guid)
    if not project:
        message = f'The project with guid:{project_guid} does not exist.'
        logging.warning(message)
        raise NotFound(message)
    return project


def file_upload(project_guid, media_file):
    project = get_project_by_guid_or_404(project_guid)
    media = ProjectMedia(project=project, media_file=media_file)
    media.full_clean()
    media.save()
    return media


@transaction.atomic()
def soft_delete_project(project):
    project.delete()
    if project.verified:
        website = project.website
        project.website.delete()
        project.website.pages.all().delete()
        project.website.domains.all().delete()
        project.website.translations.all().delete()
        get_all_website_page_versions(website.id).delete()
        create_or_update_website_in_serve_service(website)


@transaction.atomic()
def restore_deleted_project(project):
    project_deleted_at = project.deleted_at
    project.restore()
    if project.verified:
        website = project.website
        website.restore()
        deleted_at = project_deleted_at - datetime.timedelta(minutes=5)
        get_deleted_website_domains(website.id, deleted_at).restore()
        get_deleted_website_versions(website.id, deleted_at).restore()
        get_deleted_website_pages(website.id, deleted_at).restore()
        get_deleted_website_page_versions(website.id, deleted_at).restore()
        create_or_update_website_in_serve_service(website)


@transaction.atomic()
def verify_project_domain_ownership(project):
    if project.verified:
        return project
    already_verified_project = get_verified_project_by_domain(project.domain)
    if already_verified_project:
        raise ValidationError(
            f'Verified project with domain:{project.domain} already exist, contact support if you think this is a mistake!'  # noqa
        )
    check_and_verify_meta_tag(project)
    check_and_verify_platform(project.domain, project.platform)
    create_website_with_default_pages(project.id)
    project.verified = True
    project.save()
    return project


@transaction.atomic()
def force_verify_projects(projects):
    for project in projects:
        create_website_with_default_pages(project.id)
        project.verified = True
        project.save()


def create_ignore_project_class(project_guid, class_name):
    project = get_project_by_guid_or_404(project_guid)
    ignore_class = get_ignore_project_class(project.id, class_name)
    if ignore_class:
        raise ValidationError(f'Already exist class with name:{class_name}.')
    return IgnoreProjectClass.objects.create(project=project, class_name=class_name)


def delete_ignore_project_class(project_guid, class_name):
    project = get_project_by_guid_or_404(project_guid)
    ignore_class = get_ignore_project_class(project.id, class_name)
    if not ignore_class:
        raise NotFound(f'Not found class with name:{class_name}.')
    return ignore_class.delete()


def allow_ssl_for_domain(domain):
    if re.match(r'^\d{1,3}\.\d{1,}\.\d{1,3}\.\d{1,3}$', domain):
        logging.info(
            f'Not allowing ssl request for: {domain}, stopped by ip pattern match.'
        )
        return False
    if any(
        (domain.endswith(f'.{item}') or domain == item)
        for item in settings.ALLOW_SSL_GENERATION_FOR_DOMAINS
    ):
        logging.info(f'Allowing ssl request for: {domain}, linguana subdomain!')
        return True
    project = Project.objects.filter(domain=domain).first()
    if project:
        logging.info(f'Allowing ssl request for: {domain}, domain in project!')
        return True
    website_domain = get_verified_website_domains(domain)
    if website_domain:
        logging.info(f'Allowing ssl request for: {domain}, website verified domain!')
        return True
    logging.info(f'Not allowing ssl request for: {domain}')
    return False


def enable_user_disabled_projects_and_website_versions(user, sub_plan):
    try:
        projects = get_user_disabled_projects(user_id=user.id)
        if len(projects) == 0:
            return
        if sub_plan == SubscriptionPlan.STARTER:
            project = projects.first()
            website_version_ids = project.website.translations.filter(
                is_disabled=True
            ).values_list('id', flat=True)[:3]
            project.website.translations.filter(id__in=website_version_ids).update(
                is_disabled=False
            )
            project.is_disabled = False
            project.save()
            return
        elif sub_plan == SubscriptionPlan.INDIVIDUAL:
            project_ids = projects.values_list('id', flat=True)[:3]
            projects = projects.filter(id__in=project_ids)
            for project in projects:
                project.website.translations.update(is_disabled=False)
            projects.update(is_disabled=False)
            return
        elif sub_plan == SubscriptionPlan.BUSINESS:
            for project in projects:
                project.website.translations.update(is_disabled=False)
            projects.update(is_disabled=False)
        else:
            return
    except Exception as e:
        logging.error(f' Error={repr(e)}!')
        return


def create_disable_word_translation(project_guid, word):
    try:
        project = get_project_by_guid_or_404(project_guid=project_guid)
        return ProjectDisableWordTranslation.objects.create(
            project_id=project.id, word=word
        )
    except IntegrityError:
        raise ValidationError(f'This word={word} already exist!')
    except Exception:
        raise APIException(f'Failed to add word={word} to disable it from translation')
