from rest_framework import serializers
from languages.models import Language


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = (
            'guid',
            'name',
            'code',
            'translation_code',
            'emoji',
            'available',
            'local_name',
        )
