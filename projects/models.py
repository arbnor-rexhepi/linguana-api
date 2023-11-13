from django.db import models
from commons.models import BaseModel
from commons.utils import normalize_domain
from languages.models import Language
from projects.consts import PROJECT_SCREENSHOTS_FOLDER_NAME
from projects.validators import validate_file
from projects.utils import get_file_upload_path
from django.conf import settings
import logging


class ProjectPlatform(models.TextChoices):
    WEBFLOW = 'WEBFLOW'
    FRAMER = 'FRAMER'


class Project(BaseModel):
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=2000)
    main_language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='project_language',
    )
    image = models.FileField(null=True, blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    serve_in_www = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    screenshot = models.ImageField(
        upload_to=PROJECT_SCREENSHOTS_FOLDER_NAME,
        null=True,
        blank=True,
    )
    is_disabled = models.BooleanField(default=False)
    platform = models.CharField(
        max_length=100,
        choices=ProjectPlatform.choices,
        default=ProjectPlatform.WEBFLOW,
    )

    def save(self, *args, **kwargs):
        self.domain = normalize_domain(self.domain)
        super(Project, self).save(*args, **kwargs)

    @property
    def website_url(self):
        source_domain_url = f'https://{self.domain}'
        return source_domain_url.replace(
            f'https://{settings.APP_CONFIG_SUBDOMAIN_TO_SET}.', ''
        )

    @property
    def content_url(self):
        # TODO: handle www here
        return f'https://{self.domain}'

    @property
    def content_domain(self):
        return self.domain

    def get_website(self):
        try:
            return self.website
        except Exception:
            logging.info(f'Project with guid {self.guid} has no website!')
            return None

    def get_identifier(self):
        try:
            return self.identifier
        except Exception:
            logging.info(f'Website with guid {self.guid} has no identifier')
            return None

    def __str__(self):
        return self.domain

    class Meta:
        db_table = 'project'
        unique_together = ('name', 'domain', 'created_by', 'deleted_at', 'is_deleted')


class ProjectMedia(BaseModel):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='medias'
    )
    media_file = models.FileField(
        upload_to=get_file_upload_path,
        validators=[validate_file],
    )

    class Meta:
        db_table = 'project_media'


class IgnoreProjectClass(BaseModel):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='ignore_project_classes'
    )
    class_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'ignore_project_class'
        unique_together = ('project', 'class_name')


class ProjectVerificationIdentifier(BaseModel):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='identifier'
    )
    identifier = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.identifier


class ProjectDisableWordTranslation(BaseModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='disable_translations',
    )
    word = models.CharField(max_length=100)

    class Meta:
        db_table = 'project_disable_word_translation'
        unique_together = ('project', 'word')
