from django.contrib import admin
from commons.models import MaintenanceMode


class BaseModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = self.model.global_objects.all()
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    queryset = get_queryset


class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'guid',
        'status',
        'date_created',
        'date_updated',
        'expected_down_time',
    )


admin.site.register(MaintenanceMode, MaintenanceModeAdmin)
