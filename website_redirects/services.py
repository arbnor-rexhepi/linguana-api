from app.external_services.serve_redirects_services import (
    create_website_redirect_in_serve,
    update_website_redirect_in_serve,
    get_website_redirects_in_serve,
    get_website_redirect_in_serve,
    delete_website_redirect_in_serve,
)
from websites.selectors import get_website_by_project_guid_or_404
from rest_framework.exceptions import NotFound, ValidationError


def get_website_redirects(project_guid, limit, offset):
    website = get_website_by_project_guid_or_404(project_guid=project_guid)
    website_redirects = get_website_redirects_in_serve(
        website_guid=website.guid, limit=limit, offset=offset
    )
    return website_redirects


def validate_old_and_new_path(old_path, new_path):
    if old_path.lower() == new_path.lower():
        raise ValidationError('The old_path and new_path can not be the same!')


def create_website_redirect(project_guid, data):
    old_path = data.get('old_path')
    new_path = data.get('new_path')
    status = data.get('status')
    validate_old_and_new_path(old_path=old_path, new_path=new_path)
    website = get_website_by_project_guid_or_404(project_guid=project_guid)
    redirect = create_website_redirect_in_serve(
        website_guid=website.guid,
        old_path=old_path,
        new_path=new_path,
        status=status,
    )
    if not redirect:
        raise ValidationError('Cannot create website redirect. Try again!')
    return redirect


def update_website_redirect(website_redirect_guid, data):
    old_path = data.get('old_path')
    new_path = data.get('new_path')
    status = data.get('status')
    validate_old_and_new_path(old_path=old_path, new_path=new_path)
    redirect = update_website_redirect_in_serve(
        website_redirection_guid=website_redirect_guid,
        old_path=old_path,
        new_path=new_path,
        status=status,
    )
    if not redirect:
        raise ValidationError('Cannot update the website redirect. Try again!')
    return redirect


def get_website_redirect(website_redirect_guid):
    redirect = get_website_redirect_in_serve(
        website_redirect_guid=website_redirect_guid
    )
    if not redirect:
        raise NotFound(f'Not found redirect with guid:{website_redirect_guid}.')
    return redirect


def delete_website_redirect(website_redirect_guid):
    redirect = delete_website_redirect_in_serve(
        website_redirect_guid=website_redirect_guid
    )
    if not redirect:
        raise NotFound(f'Not found redirect with guid:{website_redirect_guid}.')
    return redirect
