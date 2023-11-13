from django.conf import settings
import requests
import logging
from rest_framework.exceptions import APIException


SERVE_HEADERS = {
    'Authorization': f'Bearer {settings.SERVE_API_KEY}',
    'Content-Type': 'application/json',
}
SERVE_API_LINK = f'{settings.SERVE_API_LINK}/api/v1'
REDIRECTION_SERVE_API_LINK = f'{SERVE_API_LINK}/website-redirections'


def get_website_redirects_in_serve(website_guid, limit, offset):
    try:
        api_link = f'{SERVE_API_LINK}/websites/{website_guid}/redirections?limit={limit}&offset={offset}'
        response = requests.get(api_link, headers=SERVE_HEADERS)
        return response.json()
    except Exception as e:
        message = f'Failed to get redirects for website:{website_guid}.'
        logging.error(f'{message} Error:{repr(e)}!')
        raise APIException(message)


def create_website_redirect_in_serve(website_guid, old_path, new_path, status):
    try:
        api_link = f'{REDIRECTION_SERVE_API_LINK}/'
        post_data = {
            'website_guid': str(website_guid),
            'old_path': old_path,
            'new_path': new_path,
            'status': status,
        }
        response = requests.post(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code not in [200, 201]:
            return None
        return response.json()
    except Exception as e:
        message = f'Could not create redirect for website:{website_guid}.'
        logging.error(f'{message} Error:{repr(e)}')
        raise APIException(message)


def update_website_redirect_in_serve(
    website_redirection_guid, old_path, new_path, status
):
    try:
        api_link = f'{REDIRECTION_SERVE_API_LINK}/{website_redirection_guid}/'
        post_data = {
            'old_path': old_path,
            'new_path': new_path,
            'status': status,
        }
        response = requests.put(api_link, json=post_data, headers=SERVE_HEADERS)
        if response.status_code not in [200, 201]:
            return None
        return response.json()
    except Exception as e:
        message = f'Could not update redirect for guid:{website_redirection_guid}.'
        logging.error(f'{message} Error:{repr(e)}!')
        raise APIException(message)


def get_website_redirect_in_serve(website_redirect_guid):
    try:
        api_link = f'{REDIRECTION_SERVE_API_LINK}/{website_redirect_guid}/'
        response = requests.get(api_link, headers=SERVE_HEADERS)
        if response.status_code not in [200, 201]:
            return None
        return response.json()
    except Exception as e:
        message = f'Failed to get redirect with guid:{website_redirect_guid}.'
        logging.error(f'{message} Error:{repr(e)}!')
        raise APIException(message)


def delete_website_redirect_in_serve(website_redirect_guid):
    try:
        api_link = f'{REDIRECTION_SERVE_API_LINK}/{website_redirect_guid}/'
        response = requests.delete(api_link, headers=SERVE_HEADERS)
        if response.status_code != 204:
            return None
        return True
    except Exception as e:
        message = (
            f'Failed to delete the website redirect for guid:{website_redirect_guid}.'
        )
        logging.error(f'{message} Error:{repr(e)}!')
        raise APIException(message)
