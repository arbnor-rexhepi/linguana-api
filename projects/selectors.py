from projects.models import Project, IgnoreProjectClass, ProjectDisableWordTranslation
from projects.consts import PROJECT_META_VERIFICATION_TAG_NAME
from django.db.models import Q


def get_project_meta_identifier_string(project):
    identifier_obj = project.get_identifier()
    if not identifier_obj:
        return ''
    return f'<meta name="{PROJECT_META_VERIFICATION_TAG_NAME}" content="{identifier_obj.identifier}"/>'


def get_verified_project_by_domain(domain):
    return Project.objects.filter(domain=domain, is_deleted=False, verified=True)


def get_project_by_guid(guid):
    try:
        return Project.objects.get(guid=guid)
    except Project.DoesNotExist:
        return None


def get_number_of_user_projects(user_id):
    return Project.objects.filter(created_by_id=user_id).count()


def get_number_of_user_verified_projects(user_id):
    return Project.objects.filter(created_by_id=user_id, verified=True).count()


def get_user_verified_projects(user_id):
    return Project.objects.filter(created_by_id=user_id, verified=True)


def get_ignore_project_class(project_id, class_name):
    return IgnoreProjectClass.objects.filter(
        project_id=project_id, class_name=class_name
    ).first()


def get_all_projects():
    return Project.objects.filter(Q(screenshot=None) | Q(screenshot=''))


def get_user_disabled_projects(user_id):
    return Project.objects.filter(
        created_by_id=user_id, verified=True, is_disabled=True
    ).order_by('-date_created')


def get_list_of_words_to_disable_translations(project_id):
    return ProjectDisableWordTranslation.objects.filter(
        project_id=project_id
    ).values_list('word', flat=True)
