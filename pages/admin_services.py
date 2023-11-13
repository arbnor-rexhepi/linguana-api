from django.contrib import admin
from django.contrib import messages
from pages.services import (
    get_page_elements_for_publishing,
    get_page_parsed_elements_with_translations,
    get_translated_page_content,
)
from django.http import HttpResponse
import json
from uuid import UUID


def get_page_version_from_queryset(request, queryset):
    if len(queryset) > 1:
        messages.add_message(
            request, messages.WARNING, 'This action is available only for one item.'
        )
        return
    page_version = queryset[0]
    if page_version.is_deleted:
        messages.add_message(
            request,
            messages.WARNING,
            'Page version does not exist or marked as deleted!',
        )
        return
    return page_version


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        return json.JSONEncoder.default(self, obj)


def response_file_download(filename, json_content='', content=''):
    response = HttpResponse(
        json.dumps(json_content, cls=UUIDEncoder) if json_content else content,
        content_type='application/force-download',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@admin.action(description='Get page elements with translations')
def get_elements_with_translations(modeladmin, request, queryset):
    page_version = get_page_version_from_queryset(request, queryset)
    if not page_version:
        return
    parsed_page = page_version.page.get_parsed_page()
    if not parsed_page:
        messages.add_message(request, messages.WARNING, 'This item is not parsed yet')
        return
    elements = get_page_parsed_elements_with_translations(
        page_version.page.guid, page_version.guid
    )
    return response_file_download(
        f'elements-with-translations-{page_version.guid}.json', json_content=elements
    )


@admin.action(description='Get page elements for publishing')
def get_elements_for_publishing(modeladmin, request, queryset):
    page_version = get_page_version_from_queryset(request, queryset)
    if not page_version:
        return
    parsed_page = page_version.page.get_parsed_page()
    if not parsed_page:
        messages.add_message(request, messages.WARNING, 'This item is not parsed yet')
        return
    elements = get_page_elements_for_publishing(
        page_version.page.guid, page_version.guid
    )
    return response_file_download(
        f'elements-for-publishing-{page_version.guid}.json', json_content=elements
    )


@admin.action(description='Download translated page as Html!')
def download_html_translated_page(modeladmin, request, queryset):
    page_version = get_page_version_from_queryset(request, queryset)
    if not page_version:
        return
    parsed_page = page_version.page.get_parsed_page()
    if not parsed_page:
        messages.add_message(request, messages.WARNING, 'This item is not parsed yet')
        return
    print(page_version.page.guid, page_version.guid)
    elements = get_page_elements_for_publishing(
        page_version.page.guid, page_version.guid
    )
    content = get_translated_page_content(  # noqa
        page_version.page.full_content_url,
        elements,
        page_version.page.website.project.platform,
    )
    if not content:
        messages.add_message(
            request, messages.WARNING, 'Cannot get content for this page'
        )
        return
    return response_file_download(f'html-{page_version.guid}.html', content=content)


@admin.action(description='Get parsed content!')
def get_parsed_content(modeladmin, request, queryset):
    page_version = get_page_version_from_queryset(request, queryset)
    if not page_version:
        return
    parsed_page = page_version.page.get_parsed_page()
    if not parsed_page:
        messages.add_message(request, messages.WARNING, 'This item is not parsed yet')
        return

    return response_file_download(
        f'elements-for-publishing-{page_version.guid}.json',
        content=parsed_page.parsed_elements_file,
    )
