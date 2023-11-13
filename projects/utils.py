import uuid
from projects.consts import PROJECT_IMAGE_UPLOADS_FOLDER_NAME


def get_file_upload_path(instance, filename):
    name, extension = filename.rsplit('.', 1)
    filename = f'{PROJECT_IMAGE_UPLOADS_FOLDER_NAME}/{name}-{uuid.uuid4()}.{extension}'
    return filename
