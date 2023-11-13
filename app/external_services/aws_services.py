import boto3
import base64
import logging
import json
from django.conf import settings


def takeScreenshot(url):
    try:
        lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        lambda_payload = {'url': url}
        response = lambda_client.invoke(
            FunctionName=settings.AWS_TAKE_SCREENSHOT_LAMBDA,
            Payload=json.dumps(lambda_payload),
        )
        if response['StatusCode'] != 200:
            return None
        response_payload = json.loads(response['Payload'].read().decode())
        return base64.b64decode(str(response_payload['screenshot_base64']))

    except Exception as e:
        logging.error(f'Failed to take screenshot for url:{url}! Error={repr(e)}')
        return None
