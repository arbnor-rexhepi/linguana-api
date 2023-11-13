from django.conf import settings
from projects.models import ProjectPlatform


def get_webflow_dns_config():
    return [
        {
            'record_type': 'A',
            'record_name': '@',
            'record_data': settings.APP_CONFIG_A_RECORD_IP_SETUP,
        },
        {
            'record_type': 'CNAME',
            'record_name': 'www',
            'record_data': settings.APP_CONFIG_WWW_SETUP_URL,
        },
        {
            'record_type': 'CNAME',
            'record_name': 'linguana',
            'record_data': settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY,
        },
        {
            'record_type': 'TXT',
            'record_name': '@',
            'record_data': settings.APP_CONFIG_WEBFLOW_SUBDOMAIN_PROXY,
        },
    ]


def get_framer_dns_config():
    return [
        {
            'record_type': 'A',
            'record_name': '@',
            'record_data': settings.APP_CONFIG_A_RECORD_IP_SETUP,
        },
        {
            'record_type': 'CNAME',
            'record_name': 'www',
            'record_data': settings.APP_CONFIG_WWW_SETUP_URL,
        },
        {
            'record_type': 'CNAME',
            'record_name': 'linguana',
            'record_data': settings.APP_CONFIG_FRAMER_SUBDOMAIN_PROXY,
        },
    ]


def get_project_dns_config(project):
    if project.platform == ProjectPlatform.FRAMER:
        return get_framer_dns_config()
    return get_webflow_dns_config()
