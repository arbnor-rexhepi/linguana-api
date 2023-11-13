from django.conf import settings
import logging
import firebase_admin
from firebase_admin import db
from firebase.enums import ActionType, EntityType, ActionStatus
from rest_framework.exceptions import ValidationError
import uuid
from datetime import datetime, timedelta
from rest_framework.exceptions import PermissionDenied

FIREBASE_REAL_TIME_DB_URL = settings.FIREBASE_REAL_TIME_DB_URL
if FIREBASE_REAL_TIME_DB_URL:
    app_options = {'databaseURL': FIREBASE_REAL_TIME_DB_URL}
    firebase_admin.initialize_app(options=app_options)
else:
    logging.error('FIREBASE_REAL_TIME_DB_URL is not initialized with its value!')


def save_user_batch_operations_in_firebase(
    user,
    entity_guid_id,
    entity,
    name,
    status,
    action,
    start_time,
    completed_time,
    all_items,
    completed_items,
    failed_items,
    is_read=False,
    action_type=ActionType.PROCESS.value,
):
    try:
        user_guid_id = user.guid
        entity_type = get_entity_type(entity=entity, entity_guid_id=entity_guid_id)
        if not entity_type:
            raise ValidationError(f'Does not exist entity with type:{entity_type}!')

        user_batch_operations = 'user_batch_operations'
        operation = db.reference(user_batch_operations)
        if not operation.get():
            ref = db.reference('/')
            ref.update({user_batch_operations: ''})
            operation = db.reference(user_batch_operations)

        user_obj = operation.child(f'user_guid_id_{user_guid_id}')
        if not user_obj.get():
            obj = prepare_user_object(
                entity_type=entity_type,
                user_guid_id=user_guid_id,
                entity_guid_id=entity_guid_id,
                entity=entity,
                name=name,
                status=status,
                action=action,
                start_time=start_time,
                completed_time=completed_time,
                all_items=all_items,
                completed_items=completed_items,
                failed_items=failed_items,
                is_read=is_read,
                action_type=action_type,
            )

            return operation.update(obj)

        entity_obj = user_obj.child(f'{entity_type}')
        if not entity_obj.get():
            return user_obj.update(
                prepare_entity_object(
                    entity_type=entity_type,
                    user_guid_id=user_guid_id,
                    entity_guid_id=entity_guid_id,
                    entity=entity,
                    name=name,
                    status=status,
                    action=action,
                    start_time=start_time,
                    completed_time=completed_time,
                    all_items=all_items,
                    completed_items=completed_items,
                    failed_items=failed_items,
                    is_read=is_read,
                    action_type=action_type,
                )
            )
        entity_action_obj = entity_obj.child(f'{action}')
        if not entity_action_obj.get():
            return entity_obj.update(
                prepare_entity_action_object(
                    user_guid_id=user_guid_id,
                    entity_guid_id=entity_guid_id,
                    entity=entity,
                    name=name,
                    status=status,
                    action=action,
                    start_time=start_time,
                    completed_time=completed_time,
                    all_items=all_items,
                    completed_items=completed_items,
                    failed_items=failed_items,
                    is_read=is_read,
                    action_type=action_type,
                )
            )
        if action_type == ActionType.NOTIFICATIONS.value:
            entity_action_type_obj = entity_action_obj.child(f'{action_type}')
            if not entity_action_type_obj.get():
                action_type_obj = {
                    f'{action_type}': prepare_base_notification_object(
                        user_guid_id=user_guid_id,
                        entity_guid_id=entity_guid_id,
                        all_items=all_items,
                        completed_items=completed_items,
                        failed_items=failed_items,
                    )
                }
                return entity_action_obj.update(action_type_obj)
            else:
                return entity_action_type_obj.update(
                    prepare_base_notification_object(
                        user_guid_id=user_guid_id,
                        entity_guid_id=entity_guid_id,
                        all_items=all_items,
                        completed_items=completed_items,
                        failed_items=failed_items,
                    )
                )
        else:
            return entity_action_obj.update(
                prepare_base_object(
                    user_guid_id=user_guid_id,
                    entity_guid_id=entity_guid_id,
                    entity=entity,
                    name=name,
                    status=status,
                    action=action,
                    start_time=start_time,
                    completed_time=completed_time,
                    all_items=all_items,
                    completed_items=completed_items,
                    failed_items=failed_items,
                    is_read=is_read,
                    action_type=action_type,
                )
            )
    except Exception as e:
        logging.error(
            f"""Failed to save user operation in firebase, user_email:{user.email},
            entity_guid_id:{entity_guid_id}, entity:{entity}! Error:{repr(e)}"""
        )


def get_entity_type(entity, entity_guid_id):
    if entity == EntityType.PAGE.name:
        return f'page_guid_id_{entity_guid_id}'
    elif entity == EntityType.PAGE_VERSION.name:
        return f'page_version_guid_id_{entity_guid_id}'
    elif entity == EntityType.WEBSITE_VERSION.name:
        return f'website_version_guid_id_{entity_guid_id}'
    elif entity == EntityType.PROJECT.name:
        return f'project_guid_id_{entity_guid_id}'
    else:
        return None


def prepare_user_object(
    entity_type,
    user_guid_id,
    entity_guid_id,
    entity,
    name,
    status,
    action,
    start_time,
    completed_time,
    all_items,
    completed_items,
    failed_items,
    is_read,
    action_type,
):
    return {
        f'user_guid_id_{user_guid_id}': prepare_entity_object(
            entity_type=entity_type,
            user_guid_id=user_guid_id,
            entity_guid_id=entity_guid_id,
            entity=entity,
            name=name,
            status=status,
            action=action,
            start_time=start_time,
            completed_time=completed_time,
            all_items=all_items,
            completed_items=completed_items,
            failed_items=failed_items,
            is_read=is_read,
            action_type=action_type,
        )
    }


def prepare_entity_object(
    entity_type,
    user_guid_id,
    entity_guid_id,
    entity,
    name,
    status,
    action,
    start_time,
    completed_time,
    all_items,
    completed_items,
    failed_items,
    is_read,
    action_type,
):
    return {
        f'{entity_type}': prepare_entity_action_object(
            user_guid_id=user_guid_id,
            entity_guid_id=entity_guid_id,
            entity=entity,
            name=name,
            status=status,
            action=action,
            start_time=start_time,
            completed_time=completed_time,
            all_items=all_items,
            completed_items=completed_items,
            failed_items=failed_items,
            is_read=is_read,
            action_type=action_type,
        )
    }


def prepare_entity_action_object(
    user_guid_id,
    entity_guid_id,
    entity,
    name,
    status,
    action,
    start_time,
    completed_time,
    all_items,
    completed_items,
    failed_items,
    is_read,
    action_type,
):
    return {
        f'{action}': prepare_base_object(
            user_guid_id=user_guid_id,
            entity_guid_id=entity_guid_id,
            entity=entity,
            name=name,
            status=status,
            action=action,
            start_time=start_time,
            completed_time=completed_time,
            all_items=all_items,
            completed_items=completed_items,
            failed_items=failed_items,
            is_read=is_read,
            action_type=action_type,
        )
    }


def prepare_base_object(
    user_guid_id,
    entity_guid_id,
    entity,
    name,
    status,
    action,
    start_time,
    completed_time,
    all_items,
    completed_items,
    failed_items,
    is_read,
    action_type,
):
    return {
        f'{action_type}': {
            'user_guid_id': f'{user_guid_id}',
            'entity_guid_id': f'{entity_guid_id}',
            'entity': f'{entity}',
            'name': f'{name}',
            'action': f'{action}',
            'status': f'{status}',
            'start_time': f'{start_time}',
            'completed_time': f'{completed_time}',
            'all_items': f'{all_items}',
            'completed_items': f'{completed_items}',
            'failed_items': f'{failed_items}',
            'is_read': f'{is_read}',
        }
    }


def prepare_base_notification_object(
    user_guid_id,
    entity_guid_id,
    all_items,
    completed_items,
    failed_items,
):
    notification_guid_id = uuid.uuid4()
    return {
        f'{notification_guid_id}': {
            'user_guid_id': f'{user_guid_id}',
            'entity_guid_id': f'{entity_guid_id}',
            'all_items': f'{all_items}',
            'completed_items': f'{completed_items}',
            'failed_items': f'{failed_items}',
            'created_at': f'{datetime.utcnow()}',
        }
    }


def check_if_any_batch_action_is_running_on_the_project(user, project):
    try:
        website_versions = project.website.translations.all()
        website_version_guid_ids = [version.guid for version in website_versions]
        user_guid_id = user.guid
        user_batch_operations = 'user_batch_operations'
        operation = db.reference(user_batch_operations)
        if not operation.get():
            ref = db.reference('/')
            ref.update({user_batch_operations: ''})
            operation = db.reference(user_batch_operations)

        statuses = [ActionStatus.STARTED.name, ActionStatus.PROCESSING.name]
        for version_guid_id in website_version_guid_ids:
            entity_obj = operation.child(
                f'user_guid_id_{user_guid_id}/website_version_guid_id_{version_guid_id}'
            )
            if not entity_obj.get():
                continue
            website_version_obj = entity_obj.get()
            for _, item in website_version_obj.items():
                if item[f'{ActionType.PROCESS.value}']['status'] in statuses:
                    return True
        entity_obj = operation.child(
            f'user_guid_id_{user_guid_id}/project_guid_id_{project.guid}'
        )
        project_obj = entity_obj.get()
        if project_obj:
            for _, item in project_obj.items():
                if item[f'{ActionType.PROCESS.value}']['status'] in statuses:
                    return True
        return False
    except Exception as e:
        logging.error(
            f"""Failed to check if any action is running on the project, user_email:{user.email},
            project guid:{project.guid}! Error:{repr(e)}"""
        )


def delete_users_notifications_in_firebase_older_than_a_week_ago(api_key):
    if settings.CHECK_USERS_FIREBASE_NOTIFICATION_LAMBDA_API_KEY != api_key:
        raise PermissionDenied(detail='You do not have permission to do this!')
    date_time_now_a_week_ago = datetime.today() - timedelta(days=7)
    root_key = 'user_batch_operations'
    try:
        ref = db.reference(root_key)
        user_operations = ref.get()
        if not user_operations:
            return
        for user_key, user_values in user_operations.items():
            for website_version_key, website_version_values in user_values.items():
                for action_key, action_values in website_version_values.items():
                    for action_type_key, action_type_values in action_values.items():
                        if action_type_key == ActionType.PROCESS.value:
                            action_date_time = datetime.strptime(
                                action_type_values['completed_time'],
                                '%Y-%m-%d %H:%M:%S.%f',
                            )
                            if action_date_time < date_time_now_a_week_ago:
                                ref.child(
                                    f'{user_key}/{website_version_key}/{action_key}/{action_type_key}'
                                ).delete()
                        elif action_type_key == ActionType.NOTIFICATIONS.value:
                            for (
                                notification_key,
                                notification_values,
                            ) in action_type_values.items():
                                action_date_time = datetime.strptime(
                                    notification_values['created_at'],
                                    '%Y-%m-%d %H:%M:%S.%f',
                                )
                                if action_date_time < date_time_now_a_week_ago:
                                    ref.child(
                                        f'{user_key}/{website_version_key}/{action_key}/{action_type_key}/{notification_key}'  # noqa
                                    ).delete()
                        else:
                            continue

    except Exception as e:
        logging.error(
            f'Failed to delete users notifications in firebase! Error:{repr(e)}'
        )


def update_unfinished_user_background_processes(api_key):
    if settings.GOOGLE_CLOUD_FUNCTION_API_KEY != api_key:
        raise PermissionDenied(detail="You don't have permission for this operation!")
    minutes = settings.BACKGROUND_PROCESS_LIFETIME_IN_MINUTES
    date_time_now_ten_minutes_ago = datetime.today() - timedelta(minutes=minutes)
    statuses = [ActionStatus.STARTED.name, ActionStatus.PROCESSING.name]
    root_key = 'user_batch_operations'
    try:
        ref = db.reference(root_key)
        user_operations = ref.get()
        if not user_operations:
            return
        for user_key, user_values in user_operations.items():
            for website_version_key, website_version_values in user_values.items():
                for action_key, action_values in website_version_values.items():
                    for action_type_key, action_type_values in action_values.items():
                        if action_type_key == ActionType.PROCESS.value:
                            action_date_time = datetime.strptime(
                                action_type_values['completed_time'],
                                '%Y-%m-%d %H:%M:%S.%f',
                            )
                            action_status = action_type_values['status']
                            if (
                                action_date_time < date_time_now_ten_minutes_ago
                                and action_status in statuses
                            ):
                                status = get_action_status(
                                    all_items=int(action_type_values['all_items']),
                                    completed_items=int(
                                        action_type_values['completed_items']
                                    ),
                                    failed_items=int(
                                        action_type_values['failed_items']
                                    ),
                                )
                                ref.child(
                                    f'{user_key}/{website_version_key}/{action_key}/{action_type_key}'
                                ).update({'status': f'{status}'})

    except Exception as e:
        logging.error(
            f'Failed to update user background processes in firebase! Error:{repr(e)}'
        )


def get_action_status(all_items, completed_items, failed_items):
    if all_items == completed_items:
        return ActionStatus.COMPLETED.value
    elif all_items == failed_items:
        return ActionStatus.FAILED.value
    else:
        return ActionStatus.PARTIALLY_COMPLETED.value
