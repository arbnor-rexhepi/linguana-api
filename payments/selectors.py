from payments.models import (
    Subscription,
    SubscriptionPeriod,
    SubscriptionPlan,
    SubscriptionStatus,
)
from django.db.models import Q
import datetime


def get_first_user_subscription(user_id):
    return Subscription.objects.filter(user_id=user_id).first()


def get_user_subscription(user_id):
    subscription = get_first_user_subscription(user_id)
    if not subscription:
        return Subscription(
            plan=SubscriptionPlan.FREE,
            period=SubscriptionPeriod.MONTHLY,
            status=SubscriptionStatus.ACTIVE,
        )
    return subscription


def get_users_expired_subscriptions():
    date_time_now = datetime.datetime.utcnow()
    date_time_now_after_one_year = date_time_now + datetime.timedelta(days=366)
    subscriptions = Subscription.objects.filter(
        (
            (
                Q(status=SubscriptionStatus.CANCELED)
                | Q(status=SubscriptionStatus.DOWNGRADED)
            )
            & Q(end_date__lte=date_time_now)
            & Q(period=SubscriptionPeriod.MONTHLY)
        )
        | (
            (
                Q(status=SubscriptionStatus.CANCELED)
                | Q(status=SubscriptionStatus.DOWNGRADED)
            )
            & Q(end_date__lte=date_time_now_after_one_year)
            & Q(period=SubscriptionPeriod.YEARLY)
        ),
    )
    return subscriptions
