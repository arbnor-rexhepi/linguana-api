from allauth.account.models import EmailAddress
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.forms import ValidationError
from django.utils.encoding import force_str

from authentication.utils import is_email_allowed


class CustomAccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        if not is_email_allowed(email):
            raise ValidationError('This email is not allowed!')
        return super().clean_email(email)

    def get_email_confirmation_url(self, request, emailconfirmation):
        return f'{settings.FRONTEND_HOST.strip().strip("/")}/confirm-email/{emailconfirmation.key}'

    def format_email_subject(self, subject):
        return force_str(subject)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):

        # social account already exists, so this is just a login
        if sociallogin.is_existing:
            return

        # some social logins don't have an email address
        if not sociallogin.email_addresses:
            return

        # find the first verified email that we get from this sociallogin
        verified_email = None
        for email in sociallogin.email_addresses:

            if not is_email_allowed(email.email):
                raise ValidationError('This email is not allowed!')

            if email.verified:
                verified_email = email
                break

        # no verified emails found, nothing more to do
        if not verified_email:
            return

        # check if given email address already exists as a verified email on
        # an existing user's account
        try:
            existing_email = EmailAddress.objects.get(email__iexact=email.email)
            if not existing_email.verified:
                existing_email.verified = True
                existing_email.save()
        except EmailAddress.DoesNotExist:
            return

        # if it does, connect this new social login to the existing user
        sociallogin.connect(request, existing_email.user)
