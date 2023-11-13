import random
import string

REQUEST_STATIC_ID_PART = 'bcbc78b0'
REQUEST_ID_HEADER_NAME = 'x-request-id'


def get_random_string(length):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))


def get_request_headers():
    headers = {}
    headers[REQUEST_ID_HEADER_NAME] = REQUEST_STATIC_ID_PART + get_random_string(8)
    return headers
