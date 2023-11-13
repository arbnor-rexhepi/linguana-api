from django import template
from django.conf import settings
import os

register = template.Library()

# settings value
ALLOWABLE_VALUES = ('STATIC_FILES_HOST',)


@register.simple_tag
def settings_value(name):
    if name in ALLOWABLE_VALUES:
        return getattr(settings, name, '')
    raise Exception('Settings value not allowable or missing, check custom_tags.py')


ALLOWED_KEYS = ['ENV']


@register.filter()
def environment_value(key):
    if key not in ALLOWED_KEYS:
        return ''
    return os.environ.get(key)
