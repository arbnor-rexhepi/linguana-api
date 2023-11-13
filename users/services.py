from django.conf import settings
from users.models import UserCredits, User, UserFirebaseToken, UserProfile
from allauth.account.models import EmailAddress
from payments.stripe_services import update_customer_account_in_stripe
from django.db import transaction
from rest_framework.exceptions import ValidationError
from payments.models import SubscriptionStatus
from projects.selectors import (
    get_number_of_user_verified_projects,
    get_user_verified_projects,
)
from websites.selectors import get_user_website_versions
from payments.selectors import get_users_expired_subscriptions
from rest_framework.exceptions import PermissionDenied
from commons.mail import send


def deactivate_account(account):
    account.is_active = False
    account.save()


def add_user_ai_credits(user_id, ai_credits, source=None):
    return UserCredits.objects.create(
        user_id=user_id,
        ai_credits=ai_credits,
        source=source,
    )


def get_user_ai_credits(user_id, ai_credits, source):
    return UserCredits.objects.filter(
        user_id=user_id, ai_credits=ai_credits, source=source
    ).first()


def get_user_by_email(email):
    return User.objects.filter(email=email).first()


def get_user_by_id(id):
    return User.objects.filter(id=id).first()


def check_if_exist_any_account_with_email(email):
    return EmailAddress.objects.filter(email=email).exists()


@transaction.atomic()
def update_or_create_user_profile(user, email, firstname, lastname, picture, request):
    if email and user.email != email:
        any_account_exist = check_if_exist_any_account_with_email(email)
        if any_account_exist:
            raise ValidationError(
                f'This email:{email} is used by another account, please use another email address.'
            )
        account_email = EmailAddress.objects.get_primary(user)
        account_email.change(request=request, new_email=email, confirm=True)
        update_customer_account_in_stripe(user.email, email)

    obj_defaults = {
        'firstname': firstname,
        'lastname': lastname,
    }
    if picture:
        obj_defaults = {**obj_defaults, 'picture': picture}
    profile, _ = UserProfile.objects.update_or_create(
        user=user,
        defaults=obj_defaults,
    )
    return profile


def get_user_profile(user_id):
    return UserProfile.objects.filter(user_id=user_id).first()


def check_users_expired_subscriptions(api_key):
    if settings.CHECK_USERS_SUBSCRIPTIONS_LAMBDA_API_KEY != api_key:
        raise PermissionDenied(detail='You do not have permission!')
    subscriptions = get_users_expired_subscriptions()
    for sub in subscriptions:
        user_id = sub.user_id
        if sub.status == SubscriptionStatus.CANCELED:
            disable_user_projects_and_website_versions(user_id)
        elif sub.status == SubscriptionStatus.DOWNGRADED:
            nr_projects = get_number_of_user_verified_projects(user_id)
            if nr_projects > 1:
                disable_user_projects_and_website_versions(user_id)
        else:
            pass


@transaction.atomic()
def disable_user_projects_and_website_versions(user_id):
    projects = get_user_verified_projects(user_id)
    projects.update(is_disabled=True)
    website_versions = get_user_website_versions(user_id)
    website_versions.update(is_disabled=True)


def update_or_create_user_firebase_token(user, token):
    firebase_token, _ = UserFirebaseToken.objects.update_or_create(
        user=user,
        defaults={'token': token},
    )
    return firebase_token


def get_admin_user_emails():
    return User.objects.filter(is_superuser=True).values_list('email', flat=True)


def send_email_to_admin_users(signup_user):
    admin_user_emails = get_admin_user_emails()
    if admin_user_emails:
        SUBJECT = 'NEW USER REGISTRATION'
        MESSAGE = f'User with email:{signup_user.email} registered successfully!'
        send(subject=SUBJECT, message=MESSAGE, recipients=admin_user_emails)
