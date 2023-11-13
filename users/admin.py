from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User, UserCredits, UserFirebaseToken
from commons.admin import BaseModelAdmin

from import_export.admin import ExportMixin


class UserAdmin(ExportMixin, BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password', 'name', 'last_login', 'type')}),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )

    list_display = (
        'id',
        'email',
        'guid',
        'credits_balance',
        'name',
        'is_staff',
        'last_login',
        'date_joined',
        'is_active',
        'type',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = (
        'groups',
        'user_permissions',
    )

    def credits_balance(self, obj):
        return obj.remaining_credits


admin.site.register(User, UserAdmin)


class UserCreditsAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'user',
        'ai_credits',
        'balance',
        'source',
        'guid',
        'date_created',
        'date_updated',
        'is_deleted',
    )
    list_filter = ('is_deleted',)
    search_fields = ('user__email',)
    list_per_page = 10

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('user')

    def balance(self, obj):
        return obj.balance


admin.site.register(UserCredits, UserCreditsAdmin)


class UserFirebaseTokenAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'user',
        'token',
    )
    search_fields = ('user__email',)
    list_per_page = 10


admin.site.register(UserFirebaseToken, UserFirebaseTokenAdmin)
