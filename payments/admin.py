from django.contrib import admin
from payments.models import Webhook
from payments.models import Subscription
from commons.admin import BaseModelAdmin


class SubscriptionAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'guid',
        'user',
        'plan',
        'period',
        'start_date',
        'end_date',
        'cancel_date',
        'status',
        'is_deleted',
        'deleted_at',
    )
    search_fields = ('user__email',)

    list_filter = (
        'plan',
        'period',
        'status',
    )


admin.site.register(Subscription, SubscriptionAdmin)


class WebhookAdmin(admin.ModelAdmin):
    list_display = (
        'key',
        'date_created',
        'date_updated',
    )


admin.site.register(Webhook, WebhookAdmin)
