import requests
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import NotFound
from projects.models import ProjectPlatform
from app.consts import PARSER_TIMEOUT

PARSER_HEADERS = {
    'access_token': settings.PARSER_API_KEY,
    'Content-Type': 'application/json',
}


def get_website_links(website_url):
    try:
        logging.info(f'Calling parse service for website_url for {website_url}')
        api_link = f'{settings.PARSER_API_LINK}/api/v1/website_links/'
        post_data = {'domain': website_url}
        response = requests.post(
            api_link, json=post_data, headers=PARSER_HEADERS, timeout=180
        )
        if response.status_code != status.HTTP_200_OK:
            logging.warning(
                f'Failed to get website urls for domain:{website_url}. Status from PARSER: {response.status_code}'
            )
            return None
        response_data = response.json()
        return list(set(response_data['links'] + response_data['sitemap_links']))
    except Exception as e:
        logging.error(
            f'Failed to get website urls for domain:{website_url}! Error:{repr(e)}'
        )
        return None


def check_page_url_redirect(page_url):
    try:
        logging.info(f'Checking page redirect url for {page_url}')
        api_link = f'{settings.PARSER_API_LINK}/api/v1/check_page/'
        post_data = {'page_url': page_url}
        response = requests.post(api_link, json=post_data, headers=PARSER_HEADERS)
        if response.status_code != status.HTTP_200_OK:
            logging.warning(
                f'Failed to check page url redirect for page_url:{page_url}!'
            )
            return None
        response_data = response.json()
        if response_data.get('status_code') != status.HTTP_200_OK:
            message = f'The page with url:{page_url} does not exist!'
            logging.warning(message)
            raise NotFound(message)
        redirect_to = response_data['redirected_to']
        if redirect_to:
            return redirect_to
        return page_url
    except Exception as e:
        logging.error(
            f'Failed to check page_url:{page_url} for redirect! Error:{repr(e)}'
        )
        return None


def get_page_elements(url, platform=ProjectPlatform.WEBFLOW):
    try:
        logging.info(f'Calling parse service for getting page elements for {url}')
        api_link = f'{settings.PARSER_API_LINK}/api/v1/parse_page/'
        post_data = {
            'url': url,
            'platform': platform,
        }
        response = requests.post(
            api_link,
            json=post_data,
            headers=PARSER_HEADERS,
            timeout=PARSER_TIMEOUT,
        )
        if response.status_code != status.HTTP_200_OK:
            logging.warning(
                f'Failed to get elements for page with url:{url}. Status from PARSER: {response.status_code}!'
            )
            return None
        response_data = response.json()
        return response_data
    except Exception as e:
        logging.error(f'Failed to get page elements for url:{url}! Error:{repr(e)}')
        return None


def get_translated_page_content(
    page_url, elements, platform=ProjectPlatform.WEBFLOW, custom_codes=[]
):
    try:
        logging.info(
            f'Calling parse service to get translated page content for {page_url}'
        )
        api_link = f'{settings.PARSER_API_LINK}/api/v1/translated_page_content/'
        post_data = {
            'page_url': page_url,
            'elements': elements,
            'platform': platform,
            'custom_codes': custom_codes,
        }
        response = requests.post(
            api_link,
            json=post_data,
            headers=PARSER_HEADERS,
            timeout=PARSER_TIMEOUT,
        )
        if response.status_code != status.HTTP_200_OK:
            logging.warning(
                f'Failed to create content for publishing for page url:{page_url}! Status from PARSER: {response.status_code}!'  # noqa
            )
            return None
        return response.content
    except Exception as e:
        logging.error(
            f'Failed to get translated page content for page_url:{page_url}! Error:{repr(e)}'
        )
        return None


def get_text_translation(text, src, dest):
    try:
        api_link = f'{settings.PARSER_API_LINK}/api/v1/translate/'
        post_data = {'text': text, 'src': src, 'dest': dest}
        response = requests.post(
            api_link,
            json=post_data,
            headers=PARSER_HEADERS,
            timeout=PARSER_TIMEOUT,
        )
        if response.status_code != status.HTTP_200_OK:
            logging.error(f'Failed to get text translation for this text:{text}!')
            return None
        return response.json()
    except Exception as e:
        logging.error(
            f'Failed to get text translation for text:{text}! Error:{repr(e)}'
        )
        return None
