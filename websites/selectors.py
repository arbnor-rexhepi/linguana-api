from commons.models import ServeSyncStatus
from websites.models import Website, WebsiteLangVersion, WebsiteDomain
import logging
from rest_framework.exceptions import NotFound


def get_website_by_domain(domain):
    return Website.objects.filter(domain=domain).first()


def get_website_by_guid(guid):
    return Website.objects.filter(guid=guid).first()


def get_website_by_project_guid(project_guid):
    return Website.objects.filter(project__guid=project_guid).first()


def get_website_versions(website_id):
    return WebsiteLangVersion.objects.filter(website_id=website_id)


def get_website_version_language_ids(website_id):
    return WebsiteLangVersion.objects.filter(website_id=website_id).values_list(
        'language_id', flat=True
    )


def get_website_version_by_guid(website_version_guid):
    return WebsiteLangVersion.objects.filter(guid=website_version_guid).first()


def get_website_domain_by_guid(guid):
    return WebsiteDomain.objects.filter(guid=guid).first()


def get_all_websites_with_pending_status():
    return Website.objects.filter(serve_sync_status=ServeSyncStatus.Pending)


def get_all_website_versions_with_pending_status():
    return WebsiteLangVersion.objects.filter(serve_sync_status=ServeSyncStatus.Pending)


def get_number_of_website_versions(user_id):
    return WebsiteLangVersion.objects.filter(
        website__project__created_by_id=user_id
    ).count()


def get_user_website_versions(user_id):
    return WebsiteLangVersion.objects.filter(website__project__created_by_id=user_id)


def get_website_version_by_guid_or_404(website_version_guid):
    website_version = get_website_version_by_guid(website_version_guid)
    if not website_version:
        message = (
            f'The website-version with guid:{website_version_guid} does not exist.'
        )
        logging.warning(message)
        raise NotFound(message)
    return website_version


def get_website_domain_by_guid_or_404(guid):
    website_domain = get_website_domain_by_guid(guid)
    if not website_domain:
        raise NotFound(f'The website domain with guid:{guid} does not exist!')
    return website_domain


def get_verified_website_domains(domain):
    return WebsiteDomain.objects.filter(domain=domain, is_deleted=False, verified=True)


def get_project_website_domain(project_guid, domain):
    return WebsiteDomain.objects.filter(
        website__project__guid=project_guid, domain=domain
    )


def get_deleted_website_domains(website_id, deleted_at):
    return WebsiteDomain.deleted_objects.filter(
        website_id=website_id, deleted_at__gte=deleted_at
    )


def get_deleted_website_versions(website_id, deleted_at):
    return WebsiteLangVersion.deleted_objects.filter(
        website_id=website_id, deleted_at__gte=deleted_at
    )


def get_website_versions_by_guid_ids(guid_ids):
    return WebsiteLangVersion.objects.filter(guid__in=guid_ids)


def get_website_by_project_guid_or_404(project_guid):
    website = get_website_by_project_guid(project_guid)
    if not website:
        raise NotFound(f'The project with guid:{project_guid} does not exist.')
    return website
