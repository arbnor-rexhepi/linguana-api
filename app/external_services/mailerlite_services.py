import mailerlite as MailerLite
import logging
from django.conf import settings


LINGUANA_AUTO_ADD_GROUP_ID = settings.MAILER_LITE_GROUP_ID


def send_mailer_lite_subscriber(
    email,
    name='',
    last_name='',
    ip='',
):
    try:
        if not settings.MAILER_LITE_TOKEN:
            return logging.error('Mailerlite token is not set!')
        client = MailerLite.Client({'api_key': settings.MAILER_LITE_TOKEN})
        fields = {}
        if name:
            fields['name'] = name
        if last_name:
            fields['last_name'] = last_name
        response = client.subscribers.create(
            email,
            fields=fields,
            ip_address=ip,
        )
        subscriber_id = response['data']['id']
        if subscriber_id and LINGUANA_AUTO_ADD_GROUP_ID:
            client.subscribers.assign_subscriber_to_group(
                int(subscriber_id), int(LINGUANA_AUTO_ADD_GROUP_ID)
            )
        else:
            logging.error(
                f'Subscriber id ${subscriber_id} or linguana_auto_add_group_id not set!'
            )
    except Exception as E:
        logging.error(f'Cannot add {email} subscriber to mailerlite. Error:{repr(E)}')


def update_mailer_lite_user_subscription(email, subscription):
    try:
        if not settings.MAILER_LITE_TOKEN:
            return logging.error('Mailerlite token is not set!')
        client = MailerLite.Client({'api_key': settings.MAILER_LITE_TOKEN})
        client.subscribers.update(
            email,
            fields={'subscription': subscription},
        )
    except Exception as E:
        logging.error(f'Cannot add {email} subscriber to mailerlite. Error:{repr(E)}')
