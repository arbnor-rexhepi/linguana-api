from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from app.swagger_schema_view import schema_view
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.auth.decorators import login_required
from dj_rest_auth.views import PasswordResetConfirmView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # TODO: remove confirm from here and test email reset
    path(
        'password/reset/confirm/<str:uidb64>/<str:token>',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
]


if settings.DOCUMENTATION_ENABLED:
    urlpatterns += [
        re_path(
            r'^swagger(?P<format>\.json|\.yaml)$',
            login_required(
                schema_view.without_ui(cache_timeout=0),
                login_url='/admin/login/?next=/swagger/',
            ),
            name='schema-json',
        ),
        re_path(
            r'^swagger/$',
            login_required(
                schema_view.with_ui('swagger', cache_timeout=0),
                login_url='/admin/login/?next=/swagger/',
            ),
            name='schema-swagger-ui',
        ),
        re_path(
            r'^redoc/$',
            login_required(
                schema_view.with_ui('redoc', cache_timeout=0),
                login_url='/admin/login/?next=/swagger/',
            ),
            name='schema-redoc',
        ),
    ]

urlpatterns += staticfiles_urlpatterns()
