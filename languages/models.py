from django.db import models
from commons.models import BaseModel


class Language(BaseModel):
    name = models.CharField(max_length=256)
    local_name = models.CharField(max_length=256, blank=True)
    code = models.CharField(max_length=8)
    translation_code = models.CharField(max_length=8, blank=True, null=True)
    emoji = models.CharField(max_length=20, null=True, blank=True)
    image = models.CharField(max_length=500, null=True, blank=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def ai_translation_code(self):
        return self.translation_code or self.code

    class Meta:
        db_table = 'language'
