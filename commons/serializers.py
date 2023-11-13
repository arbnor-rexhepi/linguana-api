from rest_framework import serializers
from commons.models import MaintenanceMode


class EmptySerializer(serializers.Serializer):
    data = None


class MaintenanceModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceMode
        fields = ('status', 'date_updated', 'expected_down_time')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['is_redirected'] = self.context.get('is_redirected', False)

        return response
