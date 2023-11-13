from django.conf import settings
from rest_framework.exceptions import ValidationError
import dns.resolver
import logging
import requests
from commons.headers import get_request_headers
from commons.utils import normalize_domain, split_domain
from projects.consts import PROJECT_META_VERIFICATION_TAG_NAME
from projects.models import ProjectPlatform


def flush_dns_cache():
    try:
        dns.resolver.Cache().flush()

    except Exception as e:
        logging.error(f'An error occurred while flushing DNS cache: {str(e)}')


def get_cname_or_blank(cname, domain):
    try:
        return (
            str(dns.resolver.query(f'{cname}.{domain}', 'CNAME', lifetime=60)[0].target)
            .strip('')
            .strip('.')
        )
    except Exception as E:
        logging.warning(
            f'Cannot get cname for domain: {domain} and cname:{cname}. Error:{repr(E)}'
        )
        return ''


def check_and_verify_dns_records(domain):
    # TODO: add logs here
    flush_dns_cache()
    if domain.startswith('www.'):
        domain = domain.replace('www.', '')
    try:
        a_records = dns.resolver.resolve(domain, 'A')
    except Exception as E:
        logging.warning(f'Cannot find A record for domain {domain}! Error:{repr(E)}')
        raise ValidationError(f'Cannot find requested A record for domain {domain}!')
    if len(a_records) == 0:
        logging.warning(f'A record not found for domain {domain}')
        raise ValidationError('A record not found!')
    if len(a_records) > 1:
        logging.warning(f'Found multiple A records for {domain}')
        raise ValidationError('Found multiple A records!')
    if a_records[0].address != settings.APP_CONFIG_A_RECORD_IP_SETUP:
        logging.warning(
            f'A record {settings.APP_CONFIG_A_RECORD_IP_SETUP} is not found for domain {domain}'
        )
        raise ValidationError(
            f'A record {settings.APP_CONFIG_A_RECORD_IP_SETUP} is not found!'
        )
    if get_cname_or_blank('www', domain) != settings.APP_CONFIG_WWW_SETUP_URL:
        logging.warning(
            f'The value of www CNAME for domain {domain} is different than {settings.APP_CONFIG_WWW_SETUP_URL}'
        )
        raise ValidationError(
            f'Set www as CNAME with value of {settings.APP_CONFIG_WWW_SETUP_URL}'
        )


# check if user setup linguana.domain.com in
#  webflow and also if website is running
def check_if_user_setup_project_in_our_subdomain(
    domain, platform=ProjectPlatform.WEBFLOW
):
    flush_dns_cache()
    if platform == ProjectPlatform.WEBFLOW:
        if (
            get_cname_or_blank(settings.APP_CONFIG_SUBDOMAIN_TO_SET, domain)
            != settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY
        ):
            logging.warning(
                f'The CNAME {settings.APP_CONFIG_SUBDOMAIN_TO_SET} does not have value {settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY} for domain {domain}'  # noqa
            )
            raise ValidationError(
                f'Set {settings.APP_CONFIG_SUBDOMAIN_TO_SET} as CNAME with value of {settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY}'  # noqa
            )
    if platform == ProjectPlatform.FRAMER:
        if (
            get_cname_or_blank(settings.APP_CONFIG_SUBDOMAIN_TO_SET, domain)
            != settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY
        ):
            logging.warning(
                f'The CNAME {settings.APP_CONFIG_SUBDOMAIN_TO_SET} does not have value {settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY} for domain {domain}'  # noqa
            )
            raise ValidationError(
                f'Set {settings.APP_CONFIG_SUBDOMAIN_TO_SET} as CNAME with value of {settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY}'  # noqa
            )
    try:
        response = requests.get(
            f'https://{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{domain}', timeout=20
        )
        if response.status_code != 200:
            logging.error(
                f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{domain} is not reachable right now!'
            )
            raise ValidationError(
                f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{domain} is not reachable right now!'
            )
    except Exception as E:
        logging.error(
            f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{domain} is not reachable right now! Error:{repr(E)}'
        )
        raise ValidationError(
            f'{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.{domain} is not reachable right now!'
        )


def check_and_verify_platform(domain, platform):
    domain = normalize_domain(domain)
    subdomain, domain_root = split_domain(domain)
    if platform == ProjectPlatform.WEBFLOW:
        if domain_root in ['webflow.io', 'webflow.com']:
            return True
        cname = get_cname_or_blank(subdomain or 'www', domain_root)
        if not cname:
            raise ValidationError('Project need to be hosted in Webflow.')
        if (
            cname.strip().lower()
            != settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY.strip().lower()
        ):
            raise ValidationError(
                f'Project need to be hosted in Webflow, CNAME pointed to {settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY}'
            )
        return True
    if platform == ProjectPlatform.FRAMER:
        if domain_root in ['framer.app', 'framer.website', 'framer.ai']:
            return True
        cname = get_cname_or_blank(subdomain or 'www', domain_root)
        if not cname:
            raise ValidationError('Project need to be hosted in Framer.')
        if (
            cname.strip().lower()
            != settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY.strip().lower()
        ):
            raise ValidationError(
                f'Project need to be hosted in Framer, CNAME pointed to {settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY}'
            )
        return True
    logging.error(f'Not recognized platform, for {domain}, and platform:{platform} ')


def check_and_verify_meta_tag(project):
    domain = normalize_domain(project.domain)
    try:
        headers = get_request_headers()
        response = requests.get(f'https://{domain}', headers=headers, timeout=10)
    except Exception as E:
        logging.error(
            f'Project with guid {project.guid} cannot be verified. Error:{repr(E)}'
        )
        raise ValidationError(
            'Website is not reachable at the moment, try again later!'
        )
    if response.status_code != 200:
        logging.error(
            f'Website with domain {domain} has status code {response.status_code}'
        )
        raise ValidationError(
            f'The domain:{domain} is not reachable by us at this moment!'
        )
    meta_tag_name = PROJECT_META_VERIFICATION_TAG_NAME
    meta_tag_content = (
        project.get_identifier().identifier if project.get_identifier() else ''
    )
    if meta_tag_name not in response.text or meta_tag_content not in response.text:
        logging.error(
            f'Cannot find verification meta tags on domain:{domain}, for project:{project.guid}'
        )
        raise ValidationError(f'Cannot find requested meta tags in {domain}!')


def get_final_url(url):
    headers = get_request_headers()
    url = url.strip().replace('https://', '').replace('http://', '')
    try:
        response = requests.get(f'https://{url}', timeout=10, headers=headers)
        if response.status_code == 200:
            return response.url
        else:
            logging.warning(
                f'Website with domain, cannot be reached in get_final_url. Response status:{response.status_code}'
            )
            raise ValidationError(f'Website with domain:{url} cannot be reached!')
    except Exception as E:
        logging.warning(
            f'Website with domain, cannot be reached in get_final_url, Error:{repr(E)}'
        )
        raise ValidationError(f'Website with domain:{url} cannot be reached!')
