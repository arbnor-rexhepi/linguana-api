from django.urls import path, include, re_path
from authentication.views import (
    DeleteGoogleUserAccountView,
    DeleteUserAccountView,
    GoogleLoginAuthorization,
)
from dj_rest_auth.views import PasswordResetView, PasswordResetConfirmView
from allauth.account.views import ConfirmEmailView
from dj_rest_auth.registration.views import VerifyEmailView
from authentication.views import ResendEmailVerificationView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

app_name = 'authentication'
urlpatterns = [
    re_path(r'^accounts/', include('allauth.urls'), name='socialaccount_signup'),
    path(
        'token/refresh/',
        TokenRefreshView.as_view(),
        name='refresh',
    ),
    path(
        'token/verify/',
        TokenVerifyView.as_view(),
        name='verify',
    ),
    path('', include('dj_rest_auth.urls')),
    path('registration/', include('dj_rest_auth.registration.urls')),
    path(
        'resend-verification-email/',
        ResendEmailVerificationView.as_view(),
        name='rest_resend_email',
    ),
    path('password/reset/', PasswordResetView.as_view(), name='password_reset_confirm'),
    path(
        'password/reset/confirm/<str:uidb64>/<str:token>',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path('google/', GoogleLoginAuthorization.as_view(), name='google_login'),
    path(
        'confirm-email/<str:key>/',
        ConfirmEmailView.as_view(),
        name='account_confirm_email',
    ),
    re_path(
        r'^account-confirm-email/',
        VerifyEmailView.as_view(),
        name='account_email_verification_sent',
    ),
    re_path(
        r'^account-confirm-email/(?P<key>[-:\w]+)/$',
        VerifyEmailView.as_view(),
        name='account_confirm_email',
    ),
    re_path(
        r'^user/delete/',
        DeleteUserAccountView.as_view(),
        name='delete_user_account',
    ),
    re_path(
        r'^user/delete-google-account/',
        DeleteGoogleUserAccountView.as_view(),
        name='delete_google_user_account',
    ),
]
