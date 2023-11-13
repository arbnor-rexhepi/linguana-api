from commons.services import get_maintenance_mode
from commons.serializers import MaintenanceModeSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes((AllowAny,))
def maintenance(request):
    maintenance_mode = get_maintenance_mode()
    serializer = MaintenanceModeSerializer(maintenance_mode)
    return Response(serializer.data)
