import threading
import logging
from commons.exceptions import CustomValidationError
from firebase.enums import ActionStatus, ActionType, EntityType, UserAction
from firebase.services import (
    check_if_any_batch_action_is_running_on_the_project,
    save_user_batch_operations_in_firebase,
)
from pages.background_services import (
    get_final_action_status,
)
from pages.services import (
    parse_website_pages,
    prepare_and_create_website_version_pages,
    publish_multiple_page_versions,
    sync_and_add_website_pages,
    translate_multiple_page_versions,
)
from projects.services import get_project_by_guid_or_404
from rest_framework.exceptions import ValidationError
from datetime import datetime


def publish_website_versions(
    project_guid, website_domain_guid, website_version_guid_ids, user, all
):
    project = get_project_by_guid_or_404(project_guid=project_guid)
    website_versions = project.website.translations.all()
    if not all:
        website_versions = website_versions.filter(guid__in=website_version_guid_ids)
    if len(website_versions) == 0:
        return []
    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    thread = threading.Thread(
        target=publish_website_versions_background_process,
        args=(website_domain_guid, website_versions, user),
    )
    thread.setDaemon(True)
    thread.start()
    return website_versions


def publish_website_versions_background_process(
    website_domain_guid, website_versions, user
):
    project = website_versions[0].website.project
    entity_guid_id = project.guid
    entity = EntityType.PROJECT.name
    name = project.name
    status = ActionStatus.STARTED.name
    action = UserAction.PUBLISH.name
    start_date_time = datetime.utcnow()
    all_items = len(website_versions)
    completed_items = 0
    failed_items = 0
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=start_date_time,
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
    )
    for website_version in website_versions:
        try:
            publish_multiple_page_versions(
                page_versions=website_version.pages.all(),
                website_domain_guid=website_domain_guid,
            )
            completed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
        except Exception as e:
            if not isinstance(e, ValidationError):
                logging.error(
                    f'Failed to publish website version with guid:{website_version.guid}! Error:{repr(e)}!'
                )
            failed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            continue
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=datetime.utcnow(),
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
        action_type=ActionType.NOTIFICATIONS.value,
    )


def ai_translate_website_versions(project_guid, website_version_guid_ids, user, all):
    project = get_project_by_guid_or_404(project_guid=project_guid)
    website_versions = project.website.translations.all()
    if not all:
        website_versions = website_versions.filter(guid__in=website_version_guid_ids)
    if len(website_versions) == 0:
        return []
    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    thread = threading.Thread(
        target=ai_translate_website_versions_background_process,
        args=(website_versions, user),
    )
    thread.setDaemon(True)
    thread.start()
    return website_versions


def ai_translate_website_versions_background_process(website_versions, user):
    project = website_versions[0].website.project
    entity_guid_id = project.guid
    entity = EntityType.PROJECT.name
    name = project.name
    status = ActionStatus.STARTED.name
    action = UserAction.TRANSLATE.name
    start_date_time = datetime.utcnow()
    all_items = len(website_versions)
    completed_items = 0
    failed_items = 0
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=start_date_time,
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
    )
    for website_version in website_versions:
        try:
            translate_multiple_page_versions(
                page_versions=website_version.pages.all(),
                user=user,
            )
            completed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
        except CustomValidationError:
            completed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            continue
        except Exception as e:
            if not isinstance(e, ValidationError):
                logging.error(
                    f'Failed to translate website version with guid:{website_version.guid}! Error:{repr(e)}!'
                )
            failed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            continue
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=datetime.utcnow(),
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
        action_type=ActionType.NOTIFICATIONS.value,
    )


def sync_links_and_content_website_versions(
    project_guid, website_version_guid_ids, user, all
):
    project = get_project_by_guid_or_404(project_guid=project_guid)
    website_versions = project.website.translations.all()
    if not all:
        website_versions = website_versions.filter(guid__in=website_version_guid_ids)
    if len(website_versions) == 0:
        return []
    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    thread = threading.Thread(
        target=sync_links_and_content_website_versions_background_process,
        args=(project, website_versions, user),
    )
    thread.setDaemon(True)
    thread.start()
    return website_versions


def sync_links_and_content_website_versions_background_process(
    project, website_versions, user
):
    website = project.website
    entity_guid_id = project.guid
    entity = EntityType.PROJECT.name
    name = project.name
    status = ActionStatus.PROCESSING.name
    action = UserAction.SYNC_LINKS_AND_CONTENT.name
    start_date_time = datetime.utcnow()
    all_items = len(website_versions)
    completed_items = 0
    failed_items = 0
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=start_date_time,
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
    )
    sync_links_and_parse_website_pages(website=website)
    page_ids = [page.id for page in website.pages.all()]
    for website_version in website_versions:
        try:
            website_version_page_ids = website_version.pages.values_list(
                'page_id', flat=True
            )
            new_page_ids = list(set(page_ids) - set(website_version_page_ids))
            if len(new_page_ids) > 0:
                prepare_and_create_website_version_pages(
                    website_version_id=website_version.id,
                    page_ids=new_page_ids,
                )

            completed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
        except Exception as e:
            if not isinstance(e, ValidationError):
                logging.error(
                    f'Failed to create website version pages, website_version_guid:{website_version.guid}! Error:{repr(e)}!'  # noqa
                )
            failed_items += 1
            status = get_final_action_status(
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            save_user_batch_operations_in_firebase(
                user=user,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_date_time,
                completed_time=datetime.utcnow(),
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
            )
            continue
    save_user_batch_operations_in_firebase(
        user=user,
        entity_guid_id=entity_guid_id,
        entity=entity,
        name=name,
        status=status,
        action=action,
        start_time=start_date_time,
        completed_time=datetime.utcnow(),
        all_items=all_items,
        completed_items=completed_items,
        failed_items=failed_items,
        action_type=ActionType.NOTIFICATIONS.value,
    )


def sync_links_and_parse_website_pages(website):
    try:
        sync_and_add_website_pages(website=website)
    except Exception as e:
        if not isinstance(e, ValidationError):
            logging.error(
                f'Failed to sync links and add pages, website:{website.guid}! Error:{repr(e)}!'
            )
    try:
        parse_website_pages(pages=website.pages.all())
    except Exception as e:
        if not isinstance(e, ValidationError):
            logging.error(
                f'Failed to parse website pages, website:{website.guid}! Error:{repr(e)}!'
            )
