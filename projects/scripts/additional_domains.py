from projects.models import Project, ProjectVerificationIdentifier
from django.utils.crypto import get_random_string
from websites.models import WebsiteDomainType, WebsiteDomain
from websites.services import create_default_website_subdomain
from app.external_services.serve_services import (
    create_or_update_website_domain_in_serve_service,
    create_or_update_website_in_serve_service,
)
import logging
from django.db import transaction


def add_identifiers_to_projects():
    projects = Project.objects.all()
    for project in projects:
        if not project.get_identifier():
            identifier = ProjectVerificationIdentifier.objects.create(
                project=project, identifier=get_random_string(20)
            )
            logging.info(
                f'ADDITIONAL_DOMAINS_SYNC: Added identifier {identifier.guid} to project {project.guid}'
            )
        logging.info(
            f'ADDITIONAL_DOMAINS_SYNC: Project {project.guid} already have identifier'
        )


@transaction.atomic()
def add_domains_to_verified_projects():
    projects = Project.objects.filter(verified=True, is_deleted=False)
    for project in projects:
        if 'linguana.' in project.domain:
            logging.info(
                f'ADDITIONAL_DOMAINS_SYNC: Project with guid:{project.guid} starts with linguana.'
            )
            continue
        website = project.get_website()
        if not website:
            logging.info(
                f'ADDITIONAL_DOMAINS_SYNC: Project with guid:{project.guid} does not have website.'
            )
        default_domains = website.domains.filter(
            domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN
        )
        if not default_domains:
            logging.info(
                f'ADDITIONAL_DOMAINS_SYNC: Project with guid:{project.guid} does not have default domains'
            )
            website_domain = create_default_website_subdomain(website)
            create_or_update_website_domain_in_serve_service(website_domain)
        custom_domains = website.domains.filter(
            domain_type=WebsiteDomainType.CUSTOM_ADDED
        )
        if not custom_domains:
            logging.info(
                f'ADDITIONAL_DOMAINS_SYNC: Project with guid:{project.guid} does not have custom domains'
            )
            website_domain = WebsiteDomain.objects.create(
                website=website,
                domain=project.domain,
                serve_in_www=project.serve_in_www,
                verified=True,
                domain_type=WebsiteDomainType.CUSTOM_ADDED,
            )
            create_or_update_website_domain_in_serve_service(website_domain)
        project.domain = 'linguana.' + project.domain
        project.save()
        create_or_update_website_in_serve_service(project.website)


def additional_domains_sync():
    # add identifiers to projects
    add_identifiers_to_projects()
    add_domains_to_verified_projects()
