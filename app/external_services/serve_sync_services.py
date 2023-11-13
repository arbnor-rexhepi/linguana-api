from rest_framework.exceptions import ValidationError
from commons.models import ServeSyncStatus
from app.external_services.serve_services import (
    create_or_update_website_in_serve_service,
    create_or_update_website_version_in_serve_service,
    create_or_update_website_domain_in_serve_service,
    create_or_update_website_settings_in_serve,
)
import logging


def sync_project(project):
    website = project.get_website()
    logging.info(f'Started syncing objects for project:{project.guid}')
    if not website:
        raise ValidationError('Project does not have website!')
    if website.serve_sync_status != ServeSyncStatus.Updated:
        updated = create_or_update_website_in_serve_service(website)
        if updated:
            logging.info(f'Synced website:{website.guid}')
        logging.info(f'Sync failed for website of project:{website.guid}')
    versions = website.translations.all().exclude(
        serve_sync_status=ServeSyncStatus.Updated
    )
    if versions:
        logging.info(f'Starting to sync website versions for website:{website.guid}')
        create_or_update_website_version_in_serve_service(versions)
    website_domains = website.domains.filter(verified=True)
    for website_domain in website_domains:
        create_or_update_website_domain_in_serve_service(website_domain)
    website_settings = website.get_settings()
    if website_settings:
        create_or_update_website_settings_in_serve(website)
