from django.db import models
from commons.models import BaseModel, ServeSyncStatus
from commons.utils import clean_subfolder_path
from languages.models import Language


class Website(BaseModel):
    project = models.OneToOneField(
        'projects.Project', on_delete=models.CASCADE, related_name='website'
    )
    serve_sync_status = models.CharField(
        max_length=100,
        choices=ServeSyncStatus.choices,
        default=ServeSyncStatus.Pending,
    )

    def get_settings(self):
        try:
            return self.settings
        except:  # noqa
            return None

    @property
    def website_url(self):
        return self.project.website_url

    @property
    def content_url(self):
        return self.project.content_url

    def __str__(self):
        return self.project.website_url

    class Meta:
        db_table = 'website'


class WebsiteDomainType(models.TextChoices):
    DEFAULT_SUBDOMAIN = 'DEFAULT_SUBDOMAIN'
    CUSTOM_ADDED = 'CUSTOM_ADDED'


class WebsiteDomain(BaseModel):
    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name='domains'
    )
    domain = models.CharField(max_length=2000)
    serve_in_www = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    domain_type = models.CharField(
        max_length=100,
        choices=WebsiteDomainType.choices,
        default=WebsiteDomainType.CUSTOM_ADDED,
    )

    serve_sync_status = models.CharField(
        max_length=100,
        choices=ServeSyncStatus.choices,
        default=ServeSyncStatus.Pending,
    )

    def __str__(self):
        return self.domain


class WebsiteLangVersion(BaseModel):
    website = models.ForeignKey(
        Website, on_delete=models.CASCADE, related_name='translations'
    )
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='languages'
    )
    subfolder = models.SlugField(max_length=200)
    serve_sync_status = models.CharField(
        max_length=100,
        default=ServeSyncStatus.Pending,
    )
    is_disabled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.website.project.website_url}/{self.language.code}'

    def save(self, *args, **kwargs):
        self.subfolder = clean_subfolder_path(self.subfolder)
        super().save(*args, **kwargs)

    @property
    def final_subfolder_path(self):
        return clean_subfolder_path(self.subfolder or self.language.lang_code)

    class Meta:
        db_table = 'website_lang_version'
        unique_together = ('website', 'language', 'is_deleted', 'deleted_at')


class WebsiteSettings(BaseModel):
    website = models.OneToOneField(
        Website, on_delete=models.CASCADE, related_name='settings'
    )
    show_badge = models.BooleanField(default=False)
    serve_sync_status = models.CharField(
        max_length=100,
        default=ServeSyncStatus.Pending,
    )
