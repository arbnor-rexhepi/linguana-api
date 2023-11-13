from django.db import models


class WebsiteRedirectStatus(models.IntegerChoices):
    PERMANENT = 301
    TEMPORARY = 302
