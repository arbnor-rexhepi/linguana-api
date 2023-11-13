from payments.models import SubscriptionPlan
from payments.selectors import get_user_subscription
from projects.selectors import get_number_of_user_projects
from users.models import UserType
from users.services import get_user_by_id
from rest_framework.exceptions import ValidationError
from websites.selectors import get_number_of_website_versions


def check_user_can_create_project(user_id):
    user = get_user_by_id(user_id)
    if user.type in [UserType.LIFETIME_USER, UserType.UNLIMITED]:
        return
    subscription = get_user_subscription(user_id)
    nr_of_user_projects = get_number_of_user_projects(user_id)
    plans = [SubscriptionPlan.FREE.value, SubscriptionPlan.STARTER.value]
    if subscription.plan in plans and nr_of_user_projects > 0:
        raise ValidationError(
            'You cannot create more than one project in Free or Starter plans.'
        )
    if subscription.plan == SubscriptionPlan.INDIVIDUAL and nr_of_user_projects > 2:
        raise ValidationError(
            'You cannot create more than three projects in Individual plan.'
        )


def check_user_can_create_website_versions(user_id, languages):
    user = get_user_by_id(user_id)
    if user.type in [UserType.LIFETIME_USER, UserType.UNLIMITED]:
        return

    subscription = get_user_subscription(user_id)
    nr_of_website_versions = get_number_of_website_versions(user_id)
    if (
        subscription.plan == SubscriptionPlan.FREE
        and (nr_of_website_versions + len(languages)) > 1
    ):
        raise ValidationError('You cannot create more than one language in Free plan.')
    if (
        subscription.plan == SubscriptionPlan.STARTER
        and (nr_of_website_versions + len(languages)) > 2
    ):
        raise ValidationError(
            'You cannot create more than three languages in Starter plan.'
        )


def check_user_can_create_custom_domains(user_id):
    user = get_user_by_id(user_id)
    if user.type in [UserType.LIFETIME_USER, UserType.UNLIMITED]:
        return

    subscription = get_user_subscription(user_id)
    if subscription.plan == SubscriptionPlan.FREE:
        raise ValidationError('You cannot create custom domains in Free plan.')
