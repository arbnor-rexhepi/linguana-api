from rest_framework.exceptions import ValidationError
from django.conf import settings

CONTENT_TYPES = ['image', 'video']


def validate_file(file_obj):
    content_type = file_obj.file.content_type.split('/')[0]
    if content_type not in CONTENT_TYPES:
        raise ValidationError('Not supported file, you can upload only image or video!')
    if file_obj.file.size > settings.MAX_PROJECT_MEDIA_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f'Max file size allowed is {settings.MAX_PROJECT_MEDIA_UPLOAD_SIZE_MB} MB'
        )
