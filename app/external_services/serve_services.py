from django.conf import settings
import requests
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.base import ContentFile
from commons.models import ServeSyncStatus
from websites.models import WebsiteLangVersion
from app.consts import SERVE_PUBLISHED_PAGES_FOLDER_NAME
import logging


class ServeStorage(S3Boto3Storage):
    bucket_name = settings.SERVE_BUCKET_NAME


SERVE_HEADERS = {
    'Authorization': f'Bearer {settings.SERVE_API_KEY}',
    'Content-Type': 'application/json',
}


def create_or_update_website_in_serve_service(website):
    try:
        api_link = f'{settings.SERVE_API_LINK}/api/v1/websites/'
        post_data = {
            'guid': str(website.guid),
            'domain': website.project.domain,
            'content_domain': website.project.content_domain,
            'serve_in_www': website.project.serve_in_www,
            'is_deleted': website.is_deleted,
            'platform': website.project.platform,
        }
        website.serve_sync_status = ServeSyncStatus.Syncing
        website.save()
        response = requests.post(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code in [200, 201]:
            website.serve_sync_status = ServeSyncStatus.Updated
            website.save()
            return True
        logging.warning(
            f'Failed to update serve website {website.guid}. Status form SERVE:{response.status_code}'
        )
        website.serve_sync_status = ServeSyncStatus.Failed
        website.save()
        return False
    except Exception as e:
        logging.error(f'Cannot create or update website on serve. Error:{repr(e)}')
        return False


def create_or_update_website_domain_in_serve_service(
    website_domain,
):
    try:
        api_link = f'{settings.SERVE_API_LINK}/api/v1/website-additional-domains/'
        post_data = {
            'guid': str(website_domain.guid),
            'website_guid': str(website_domain.website.guid),
            'domain': website_domain.domain,
            'serve_in_www': website_domain.serve_in_www,
            'is_deleted': website_domain.is_deleted,
        }
        website_domain.serve_sync_status = ServeSyncStatus.Syncing
        website_domain.save()
        response = requests.post(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code in [200, 201]:
            website_domain.serve_sync_status = ServeSyncStatus.Updated
            website_domain.save()
            return True
        logging.warning(
            f'Failed to update serve website {website_domain.guid}. Status form SERVE:{response.status_code}'  # noqa
        )
        website_domain.serve_sync_status = ServeSyncStatus.Failed
        website_domain.save()
        return False
    except Exception as e:
        logging.error(
            f'Cannot create or update website domain on serve. Error:{repr(e)}'
        )
        return False


def create_or_update_website_version_in_serve_service(website_versions):
    try:
        versions = [
            {
                'guid': str(version.guid),
                'website_guid': str(version.website.guid),
                'lang_code': version.language.code,
                'subfolder_slug': version.subfolder or version.language.code,
                'is_deleted': version.is_deleted,
            }
            for version in website_versions
        ]
        api_link = f'{settings.SERVE_API_LINK}/api/v1/website-versions/'
        post_data = {'versions': versions}
        WebsiteLangVersion.global_objects.filter(
            id__in=[version.id for version in website_versions]
        ).update(serve_sync_status=ServeSyncStatus.Syncing)
        response = requests.post(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code in [200, 201]:
            serve_versions = response.json()
            updated_guids = [
                version.get('guid') for version in serve_versions if version.get('guid')
            ]
            if updated_guids:
                for version in website_versions:
                    if str(version.guid) in updated_guids:
                        version.serve_sync_status = ServeSyncStatus.Updated
                    else:
                        logging.error(
                            f'Could not update website version {version.guid}!'
                        )
                        version.serve_sync_status = ServeSyncStatus.Failed
            WebsiteLangVersion.global_objects.bulk_update(
                website_versions, ['serve_sync_status']
            )
            return True
        logging.warning(
            f'Failed to update serve versions for {website_versions[0].guid}. Status form SERVE:{response.status_code}'
        )
        return False
    except Exception as e:
        logging.error(
            f'Cannot create or update website version on serve. Error:{repr(e)}'
        )
        return False


def create_or_update_page_version_in_serve(
    page_version, html_content, is_deleted=False, website_domain_guid=None
):
    try:
        api_link = f'{settings.SERVE_API_LINK}/api/v1/translated-pages-content/'

        file = None
        if not is_deleted:
            serve_storage = ServeStorage()
            file = serve_storage.save(
                f'{SERVE_PUBLISHED_PAGES_FOLDER_NAME}/published-{page_version.guid}.html',
                ContentFile(html_content, name=f'published-{page_version.guid}.html'),
            )
            html_content = file

        post_data = {
            'website_version_guid': str(page_version.website_lang_version.guid),
            'website_domain_guid': str(website_domain_guid),
            'page_version_guid': str(page_version.guid),
            'custom_page_path': page_version.page_path,
            'html_content': html_content,
            'page_path': page_version.page.page_url,
            'page_type': 'OTHER',
            'is_deleted': is_deleted,
        }
        response = requests.post(
            api_link, json=post_data, headers=SERVE_HEADERS, timeout=120
        )
        if response.status_code in [200, 201]:
            return True
        logging.warning(
            f'Page could not published with guid {page_version}. Status form SERVE:{response.status_code}'
        )
        # TODO: handle not created website in serve
        return False
    except Exception as e:
        logging.error(f'Cannot publish the page. Error:{repr(e)}')
        return False


def create_or_update_website_settings_in_serve(website):
    website_settings = website.get_settings()
    if not settings:
        logging.warning(f'No settings for website {website.guid}')
    try:
        api_link = f'{settings.SERVE_API_LINK}/api/v1/website-settings/'
        post_data = {
            'guid': str(website.guid),
            'website_guid': str(website.guid),
            'show_badge': website_settings.show_badge,
        }
        website_settings.serve_sync_status = ServeSyncStatus.Syncing
        website_settings.save()
        response = requests.post(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code in [200, 201]:
            website_settings.serve_sync_status = ServeSyncStatus.Updated
            website_settings.save()
            return True
        logging.warning(
            f'Could not update settings for website {website.guid}. Status form SERVE:{response.text}'
        )
        website_settings.serve_sync_status = ServeSyncStatus.Failed
        website_settings.save()
        return False
    except Exception as e:
        logging.error(
            f'Could not update settings for website {website.guid}\n Error:{repr(e)}'
        )
        return False
