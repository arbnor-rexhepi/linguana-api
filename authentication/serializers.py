from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer, PasswordResetSerializer
from django.conf import settings
from authentication.forms import PasswordResetFormAllowNoPassword
from users.services import deactivate_account
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer,
    TokenVerifySerializer,
)


class CustomRegisterSerializer(RegisterSerializer):
    username = None

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
        }


class CustomLoginSerializer(LoginSerializer):
    username = None

    def validate_email_verification_status(self, user):
        if (
            user.email_confirmation_expire_days
            > settings.ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS
        ):
            deactivate_account(user)
            raise serializers.ValidationError(
                ('Your account is deactivated because your email is not verified.')
            )


class CustomPasswordResetSerializer(PasswordResetSerializer):
    password_reset_form_class = PasswordResetFormAllowNoPassword

    def get_email_options(self):
        return {
            'subject_template_name': 'registration/custom_password_reset_subject.txt',
            'html_email_template_name': 'registration/password_reset.html',
            'extra_email_context': {'frontend_host': f'{settings.FRONTEND_HOST}'},
        }


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Inherit from `TokenRefreshSerializer` and touch the database
    before re-issuing a new access token and ensure that the user
    exists and is active.
    """

    error_msg = 'No active account found with the given credentials'

    def validate(self, attrs):
        token_payload = None
        try:
            token_payload = token_backend.decode(attrs['refresh'])
        except:  # noqa
            pass
        if not token_payload:
            return super().validate(attrs)
        try:
            user = get_user_model().objects.get(pk=token_payload['user_id'])
        except get_user_model().DoesNotExist:
            raise exceptions.AuthenticationFailed(self.error_msg, 'no_active_account')

        if not user.is_active or user.id != token_payload['user_id']:
            raise exceptions.AuthenticationFailed(self.error_msg, 'no_active_account')

        return super().validate(attrs)

    def to_representation(self, instance):
        return super().to_representation(instance)


class CustomTokenVerifySerializer(TokenVerifySerializer):
    error_msg = 'No active account found with the given credentials'

    def validate(self, attrs):
        token_payload = None
        try:
            token_payload = token_backend.decode(attrs['token'])
        except:  # noqa
            pass
        if not token_payload:
            return super().validate(attrs)
        try:
            user = get_user_model().objects.get(pk=token_payload['user_id'])
        except get_user_model().DoesNotExist:
            raise exceptions.AuthenticationFailed(self.error_msg, 'no_active_account')

        if not user.is_active or user.id != token_payload['user_id']:
            raise exceptions.AuthenticationFailed(self.error_msg, 'no_active_account')

        return super().validate(attrs)
