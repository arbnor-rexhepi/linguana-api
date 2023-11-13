from django.contrib import admin

from websites.models import Website, WebsiteLangVersion, WebsiteDomain, WebsiteSettings
from commons.admin import BaseModelAdmin
from websites.services import restore_deleted_website_version
from django.utils.translation import ngettext
from django.contrib import messages
from payments.selectors import get_user_subscription


class WebsiteAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'project',
        'website_url',
        'content_url',
        'serve_sync_status',
        'is_deleted',
        'deleted_at',
        'date_created',
        'date_updated',
    )

    search_fields = ('project__name', 'project__domain')

    list_filter = (
        'is_deleted',
        'serve_sync_status',
    )


admin.site.register(Website, WebsiteAdmin)


@admin.action(description='Restore selected website versions')
def restore_website_version(self, request, queryset):
    queryset = queryset.filter(is_deleted=True)
    nr_of_website_versions = len(queryset)
    if nr_of_website_versions < 1:
        return

    for version in queryset:
        restore_deleted_website_version(version)

    self.message_user(
        request,
        ngettext(
            '%d website versions was restored successfully.',
            '%d website versions were restored successfully.',
            nr_of_website_versions,
        )
        % nr_of_website_versions,
        messages.SUCCESS,
    )


class WebsiteLangVersionAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'website',
        'subfolder',
        'language',
        'serve_sync_status',
        'date_updated',
        'is_deleted',
        'deleted_at',
        'date_created',
        'date_updated',
        'is_disabled',
    )

    search_fields = ('website__project__name', 'website__project__domain')

    list_filter = (
        'is_deleted',
        'serve_sync_status',
    )
    actions = [restore_website_version]


admin.site.register(WebsiteLangVersion, WebsiteLangVersionAdmin)


class WebsiteDomainAdmin(BaseModelAdmin):
    search_fields = ['domain', 'website__project__domain']
    list_filter = [
        'serve_in_www',
        'verified',
        'domain_type',
        'is_deleted',
    ]
    list_display = (
        'id',
        'guid',
        'user_email',
        'user_type',
        'user_subscription',
        'website',
        'domain',
        'serve_in_www',
        'serve_sync_status',
        'verified',
        'domain_type',
        'is_deleted',
        'deleted_at',
        'date_created',
        'date_updated',
    )

    def user_email(self, obj):
        return obj.website.project.created_by.email

    def user_type(self, obj):
        return obj.website.project.created_by.type

    def user_subscription(self, obj):
        sub = get_user_subscription(obj.website.project.created_by.id)
        if not sub:
            return '-'
        else:
            return f'{sub.plan}-{sub.status}'


admin.site.register(WebsiteDomain, WebsiteDomainAdmin)


class WebsiteSettingsAdmin(BaseModelAdmin):
    list_display = ('website', 'show_badge')


admin.site.register(WebsiteSettings, WebsiteSettingsAdmin)
