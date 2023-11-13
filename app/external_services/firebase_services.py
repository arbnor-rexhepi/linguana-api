import json
import requests
from django.conf import settings
import logging


def send_notification(user_firebase_token, message_title, message_desc):
    fcm_api_key = settings.FCM_API_KEY

    if not fcm_api_key:
        logging.error('FCM api key is not valid, please check it!')

    url = 'https://fcm.googleapis.com/fcm/send'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'key=' + fcm_api_key,
    }

    payload = {
        'to': user_firebase_token,
        'priority': 'high',
        'notification': {
            'body': message_desc,
            'title': message_title,
        },
    }

    result = requests.post(url, data=json.dumps(payload), headers=headers)

    if result.status_code != 200:
        logging.error(
            f'Failed to send notification for user with token:{user_firebase_token}'
        )
        return False
    return True
