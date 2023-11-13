from django.contrib import admin
from languages.models import Language
from commons.admin import BaseModelAdmin


class LanguageAdmin(BaseModelAdmin):
    list_display = ('id', 'guid', 'code', 'name', 'translation_code', 'local_name')


admin.site.register(Language, LanguageAdmin)
