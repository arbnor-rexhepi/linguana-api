from django.contrib import admin
from projects.models import Project, ProjectMedia, ProjectVerificationIdentifier
from commons.admin import BaseModelAdmin
from projects.services import force_verify_projects, restore_deleted_project
from django.utils.translation import ngettext
from django.contrib import messages


@admin.action(description='Restore selected projects')
def restore_project(self, request, queryset):
    queryset = queryset.filter(is_deleted=True)
    nr_of_projects = len(queryset)
    if nr_of_projects < 1:
        return

    for project in queryset:
        restore_deleted_project(project)

    self.message_user(
        request,
        ngettext(
            '%d project was restored successfully.',
            '%d projects were restored successfully.',
            nr_of_projects,
        )
        % nr_of_projects,
        messages.SUCCESS,
    )


@admin.action(description='Force verify projects')
def force_verify_project(self, request, queryset):
    projects = queryset.filter(is_deleted=False)
    nr_of_projects = len(projects)
    if nr_of_projects < 1:
        return

    force_verify_projects(projects=projects)

    self.message_user(
        request,
        ngettext(
            '%d project was verified successfully.',
            '%d projects were verified successfully.',
            nr_of_projects,
        )
        % nr_of_projects,
        messages.SUCCESS,
    )


class ProjectAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'platform',
        'name',
        'domain',
        'serve_in_www',
        'image',
        'created_by',
        'verified',
        'is_deleted',
        'deleted_at',
        'date_created',
        'date_updated',
        'verified_domains',
        'is_disabled',
    )
    search_fields = ('name', 'created_by__email', 'domain')
    list_filter = (
        'verified',
        'is_deleted',
    )
    actions = [restore_project, force_verify_project]

    def verified_domains(self, obj):
        domains = obj.website.domains.filter(verified=True)
        return [''.join(item.domain) for item in domains] if len(domains) > 0 else None


admin.site.register(Project, ProjectAdmin)


class ProjectMediaAdmin(BaseModelAdmin):
    list_display = ('id', 'guid', 'media_file', 'date_created')


admin.site.register(ProjectMedia, ProjectMediaAdmin)


class ProjectVerificationIdentifierAdmin(BaseModelAdmin):
    list_display = (
        'project',
        'identifier',
        'is_deleted',
        'deleted_at',
        'date_created',
        'date_updated',
    )


admin.site.register(ProjectVerificationIdentifier, ProjectVerificationIdentifierAdmin)
