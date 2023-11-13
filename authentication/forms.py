from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model


class PasswordResetFormAllowNoPassword(PasswordResetForm):
    def get_users(self, email):
        active_users = get_user_model()._default_manager.filter(
            email__iexact=email, is_active=True
        )
        return active_users
