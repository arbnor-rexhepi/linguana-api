from rest_framework import serializers
from website_redirects.models import WebsiteRedirectStatus


class WebsiteRedirectSerializer(serializers.Serializer):
    guid = serializers.CharField(read_only=True)
    old_path = serializers.CharField(required=False, allow_blank=True)
    new_path = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=WebsiteRedirectStatus.choices)
