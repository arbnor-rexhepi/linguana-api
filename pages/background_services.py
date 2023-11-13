from datetime import datetime
import logging
import threading
from commons.exceptions import CustomValidationError
from firebase.services import (
    check_if_any_batch_action_is_running_on_the_project,
    save_user_batch_operations_in_firebase,
)
from firebase.enums import ActionType, EntityType, ActionStatus, UserAction
from pages.enums import PageViewActionName
from pages.services import (
    publish_page_version,
    parse_page,
    translate_page_version,
    sync_and_add_website_version_pages,
    unpublish_page_version,
)
from websites.selectors import get_website_version_by_guid_or_404
from rest_framework.exceptions import ValidationError, NotFound


def get_final_action_status(all_items, completed_items, failed_items):
    if all_items == completed_items:
        return ActionStatus.COMPLETED.value
    elif all_items == failed_items:
        return ActionStatus.FAILED.value
    elif all_items == completed_items + failed_items:
        return ActionStatus.PARTIALLY_COMPLETED.value
    else:
        return ActionStatus.PROCESSING.value


def sync_or_ai_translate_selected_website_version_pages(
    website_version_guid, page_version_guid_ids, user, all, view_action_name
):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    page_versions = website_version.pages.all()
    if not all:
        page_versions = page_versions.filter(guid__in=page_version_guid_ids)

    if len(page_versions) == 0:
        return []

    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=website_version.website.project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    if view_action_name == PageViewActionName.SYNC_CONTENT.value:
        thread = threading.Thread(
            target=parse_page_versions_background_process,
            args=(page_versions, user),
        )
    elif view_action_name == PageViewActionName.AI_TRANSLATE.value:
        thread = threading.Thread(
            target=ai_translate_page_versions_background_process,
            args=(page_versions, user),
        )
    elif view_action_name == PageViewActionName.SYNC_LINKS_AND_CONTENT.value:
        thread = threading.Thread(
            target=sync_links_and_parse_content_of_page_versions_background_process,
            args=(page_versions, user),
        )
    else:
        raise ValidationError('API not supported this request!')
    thread.setDaemon(True)
    thread.start()
    return page_versions


def sync_links_and_parse_content_of_page_versions_background_process(
    page_versions, user
):
    website_version_guid = page_versions[0].website_lang_version.guid
    try:
        sync_and_add_website_version_pages(website_version_guid=website_version_guid)
    except Exception as e:
        if not isinstance(e, ValidationError):
            logging.error(
                f'Failed to sync page links for website version with guid:{website_version_guid}! Error:{repr(e)}!'
            )
    try:
        parse_page_versions_background_process(
            page_versions, user, action=UserAction.SYNC_LINKS_AND_CONTENT.name
        )
    except Exception as e:
        if not isinstance(e, ValidationError):
            logging.error(
                f'Failed to sync content of page versions for website version with guid:{website_version_guid}! Error:{repr(e)}!'  # noqa
            )


def parse_page_versions_background_process(
    page_versions, user, action=UserAction.PARSE.name
):
    website_version = page_versions[0].website_lang_version
    entity_guid_id = website_version.guid
    entity = EntityType.WEBSITE_VERSION.name
    name = f'{website_version.website.project.name}/{website_version.language.name}'
    status = ActionStatus.STARTED.name
    start_date_time = datetime.utcnow()
    all_items = len(page_versions)
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
    for version in page_versions:
        page_guid = version.page.guid
        try:
            parse_page(page_guid=page_guid)
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
                    f'Failed to parse page with guid:{page_guid}! Error:{repr(e)}!'
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


def ai_translate_page_versions_background_process(page_versions, user):
    website_version = page_versions[0].website_lang_version
    entity_guid_id = website_version.guid
    entity = EntityType.WEBSITE_VERSION.name
    name = f'{website_version.website.project.name}/{website_version.language.name}'
    status = ActionStatus.STARTED.name
    action = UserAction.TRANSLATE.name
    start_date_time = datetime.utcnow()
    all_items = len(page_versions)
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
    for version in page_versions:
        page_version_guid = version.guid
        try:
            translate_page_version(
                page_version_guid=page_version_guid,
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
                    f'Failed to translate page version with guid:{page_version_guid}! Error:{repr(e)}!'
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


def publish_selected_website_version_pages(
    website_version_guid, website_domain_guid, page_version_guid_ids, user, all
):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    page_versions = website_version.pages.all()
    if not all:
        page_versions = page_versions.filter(guid__in=page_version_guid_ids)
    if len(page_versions) == 0:
        return []

    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=website_version.website.project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    thread = threading.Thread(
        target=publish_page_versions_background_process,
        args=(website_domain_guid, page_versions, user),
    )
    thread.setDaemon(True)
    thread.start()
    return page_versions


def publish_page_versions_background_process(website_domain_guid, page_versions, user):
    website_version = page_versions[0].website_lang_version
    entity_guid_id = website_version.guid
    entity = EntityType.WEBSITE_VERSION.name
    name = f'{website_version.website.project.name}/{website_version.language.name}'
    status = ActionStatus.STARTED.name
    action = UserAction.PUBLISH.name
    start_date_time = datetime.utcnow()
    all_items = len(page_versions)
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
    for version in page_versions:
        page_version_guid = version.guid
        try:
            publish_page_version(
                page_guid=page_version_guid,
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
            if not (isinstance(e, NotFound) or isinstance(e, ValidationError)):
                logging.error(
                    f'Failed to publish page version with guid:{page_version_guid}! Error:{repr(e)}!'
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


def unpublish_page_versions(
    website_version_guid, website_domain_guid, page_version_guid_ids, user, all
):
    website_version = get_website_version_by_guid_or_404(website_version_guid)
    page_versions = website_version.pages.all()
    if not all:
        page_versions = page_versions.filter(guid__in=page_version_guid_ids)
    if len(page_versions) == 0:
        return []

    is_running = check_if_any_batch_action_is_running_on_the_project(
        user=user, project=website_version.website.project
    )

    if is_running:
        raise ValidationError(
            'Another process is running on this project, please wait for it to finish!'
        )
    thread = threading.Thread(
        target=unpublish_page_versions_background_process,
        args=(website_domain_guid, page_versions, user),
    )
    thread.setDaemon(True)
    thread.start()
    return page_versions


def unpublish_page_versions_background_process(
    website_domain_guid, page_versions, user
):
    website_version = page_versions[0].website_lang_version
    entity_guid_id = website_version.guid
    entity = EntityType.WEBSITE_VERSION.name
    name = f'{website_version.website.project.name}/{website_version.language.name}'
    status = ActionStatus.STARTED.name
    action = UserAction.UNPUBLISH.name
    start_date_time = datetime.utcnow()
    all_items = len(page_versions)
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
    for version in page_versions:
        page_version_guid = version.guid
        try:
            unpublish_page_version(
                page_version_guid=page_version_guid,
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
            if not (isinstance(e, NotFound) or isinstance(e, ValidationError)):
                logging.error(
                    f'Failed to publish page version with guid:{page_version_guid}! Error:{repr(e)}!'
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
