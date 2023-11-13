from pages.models import Page, PageLangVersion, PageVersionCustomCode
from websites.models import WebsiteLangVersion
from django.db.models import Q


def get_website_version_all_pages(website_version_guid):
    website_version = WebsiteLangVersion.objects.filter(
        guid=website_version_guid
    ).first()
    if not website_version:
        return []
    return website_version.website.pages.all()


def get_website_pages(website_id):
    return Page.objects.filter(website_id=website_id)


def get_website_page_urls(website_id):
    return Page.global_objects.filter(website_id=website_id).values_list(
        'page_url', flat=True
    )


def get_website_page_ids(guid_ids):
    return Page.objects.filter(guid__in=guid_ids).values_list('id', flat=True)


def get_website_pages_by_guid_ids(guid_ids):
    return Page.objects.filter(guid__in=guid_ids)


def get_website_version_pages(website_version_guid):
    return PageLangVersion.objects.filter(
        website_lang_version__guid=website_version_guid
    )


def get_website_version_selected_pages_ids(website_version_guid):
    return PageLangVersion.objects.filter(
        website_lang_version__guid=website_version_guid
    ).values_list('page_id', flat=True)


def get_website_version_page_ids(website_version_id):
    return PageLangVersion.objects.filter(
        website_lang_version_id=website_version_id
    ).values_list('page_id', flat=True)


def check_page_version_exist(website_version_guid, page_id):
    return PageLangVersion.objects.filter(
        website_lang_version__guid=website_version_guid, page_id=page_id
    ).exists()


def get_page_version_by_guid(guid):
    return PageLangVersion.objects.filter(guid=guid).first()


def get_page_by_guid(guid):
    return Page.objects.filter(guid=guid).first()


def get_total_number_of_website_page_versions(website_version_id):
    return PageLangVersion.objects.filter(
        website_lang_version_id=website_version_id
    ).count()


def get_all_website_page_versions(website_id):
    return PageLangVersion.objects.filter(website_lang_version__website_id=website_id)


def get_deleted_website_page_versions(website_id, deleted_at):
    return PageLangVersion.deleted_objects.filter(
        website_lang_version__website_id=website_id, deleted_at__gte=deleted_at
    )


def get_deleted_website_pages(website_id, deleted_at):
    return Page.deleted_objects.filter(
        website_id=website_id, deleted_at__gte=deleted_at
    )


def get_page_version_custom_codes(project_id, website_version_id, page_version_id):
    return PageVersionCustomCode.objects.filter(
        Q(project_id=project_id)
        | Q(website_version_id=website_version_id)
        | Q(page_version_id=page_version_id)
    ).select_related('project', 'website_version', 'page_version')
