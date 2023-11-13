from commons.models import MaintenanceStatus
from commons.services import get_maintenance_mode
from rest_framework.response import Response
from commons.serializers import MaintenanceModeSerializer
from rest_framework.renderers import JSONRenderer
from rest_framework import status


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get('PATH_INFO', '')
        maintenance = get_maintenance_mode()
        if (
            maintenance
            and maintenance.status == MaintenanceStatus.DOWN
            and 'admin' not in path
            and 'maintenance' not in path
        ):
            data = MaintenanceModeSerializer(
                instance=maintenance, context={'is_redirected': True}
            ).data
            response = Response(data=data, status=status.HTTP_200_OK)
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = 'application/json'
            response.renderer_context = {}
            response.render()
            return response
        response = self.get_response(request)
        return response
