from django.db import models
from commons.models import BaseModel
from commons.utils import normalize_page_url
from pages.enums import PageType
from projects.models import Project
from websites.models import Website, WebsiteLangVersion, WebsiteDomain
from pages.consts import PARSED_FILES_FOLDER_NAME


class PageStatus(models.TextChoices):
    ACTIVE = 'ACTIVE'
    LINK_NOT_FOUND = 'LINK_NOT_FOUND'
    PAGE_NOT_FOUND = 'PAGE_NOT_FOUND'


class Page(BaseModel):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='pages')
    page_url = models.CharField(max_length=10000, blank=True)
    nr_of_words = models.IntegerField(default=0)
    status = models.CharField(
        max_length=100,
        choices=PageStatus.choices,
        default=PageStatus.ACTIVE,
    )

    class Meta:
        db_table = 'page'
        unique_together = ('website', 'page_url', 'deleted_at', 'is_deleted')

    @property
    def full_content_url(self):
        if self.page_url == PageType.Home.value:
            return self.website.content_url
        return f'{self.website.content_url}/{self.page_url}'

    @property
    def full_url(self):
        if self.page_url == PageType.Home.value:
            return self.website.project.website_url
        return f'{self.website.project.website_url}/{self.page_url}'

    @property
    def display_name(self):
        if self.page_url == PageType.Home.value:
            return PageType.Home.name
        elif self.page_url == PageType.Page404.value:
            return PageType.Page404.name
        elif self.page_url == PageType.Sitemap.value:
            return PageType.Sitemap.name
        else:
            return self.page_url.strip('/')

    def get_parsed_page(self):
        try:
            return self.parsed_page
        except:  # noqa
            return None

    def __str__(self):
        return str(self.guid)

    def save(self, *args, **kwargs):
        self.page_url = normalize_page_url(self.page_url)
        super(Page, self).save(*args, **kwargs)


class PageLangVersion(BaseModel):
    website_lang_version = models.ForeignKey(
        WebsiteLangVersion, on_delete=models.CASCADE, related_name='pages'
    )
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    custom_page_url = models.CharField(max_length=10000, null=True, blank=True)

    class Meta:
        db_table = 'page_lang_version'
        ordering = ('-date_created',)
        unique_together = (
            'page',
            'website_lang_version',
            'custom_page_url',
            'deleted_at',
            'is_deleted',
        )

    def save(self, *args, **kwargs):
        if self.custom_page_url is not None:
            self.custom_page_url = normalize_page_url(self.custom_page_url)
        super(PageLangVersion, self).save(*args, **kwargs)

    @property
    def page_path(self):
        return self.custom_page_url or self.page.page_url

    @property
    def live_translated_page_url(self):
        return f'{self.website_lang_version.website.website_url}/{self.website_lang_version.subfolder}/{self.page_path}'.strip(  # noqa
            '/'
        )

    @property
    def translated_page_path(self):
        return f'{self.website_lang_version.subfolder}/{self.page_path}'.strip('/')

    def __str__(self) -> str:
        return f'{self.guid}'


class ParsedPage(BaseModel):
    page = models.OneToOneField(
        Page, on_delete=models.CASCADE, related_name='parsed_page'
    )
    parsed_elements_file = models.FileField(upload_to=PARSED_FILES_FOLDER_NAME)

    class Meta:
        db_table = 'parsed_page'


class PublishedPageStatus(models.TextChoices):
    PUBLISHED = 'PUBLISHED'
    UNPUBLISHED = 'UNPUBLISHED'


class PublishedPageVersionStatus(BaseModel):
    page_version = models.ForeignKey(
        PageLangVersion, on_delete=models.CASCADE, related_name='published_pages'
    )
    failed = models.BooleanField(default=False)
    domain = models.ForeignKey(WebsiteDomain, on_delete=models.CASCADE, null=True)
    status = models.CharField(
        max_length=100,
        choices=PublishedPageStatus.choices,
        default=PublishedPageStatus.PUBLISHED,
    )

    def __str__(self):
        return str(self.page_version)

    @property
    def published_at(self):
        return self.date_created

    class Meta:
        db_table = 'published_page_version_status'


class PageVersionCustomCode(BaseModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_codes',
    )
    website_version = models.ForeignKey(
        WebsiteLangVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_codes',
    )
    page_version = models.ForeignKey(
        PageLangVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_codes',
    )
    head_code = models.CharField(max_length=250, null=True, blank=True)
    body_code = models.CharField(max_length=250, null=True, blank=True)

    class Meta:
        db_table = 'page_version_custom_code'
