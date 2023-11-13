from django.db import models
from commons.models import BaseModel


class ProductType(models.TextChoices):
    SUBSCRIPTION = 'SUBSCRIPTION'
    CREDITS = 'CREDITS'


class SubscriptionPlan(models.TextChoices):
    FREE = 'FREE'
    STARTER = 'STARTER'
    INDIVIDUAL = 'INDIVIDUAL'
    BUSINESS = 'BUSINESS'


class SubscriptionPeriod(models.TextChoices):
    MONTHLY = 'MONTHLY'
    YEARLY = 'YEARLY'


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'ACTIVE'
    DOWNGRADED = 'DOWNGRADED'
    UPGRADED = 'UPGRADED'
    CANCELED = 'CANCELED'


class Subscription(BaseModel):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    plan = models.CharField(
        max_length=100,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
    )
    period = models.CharField(
        max_length=100,
        choices=SubscriptionPeriod.choices,
        default=SubscriptionPeriod.MONTHLY,
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    cancel_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=100,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )

    class Meta:
        db_table = 'subscription'


class Webhook(BaseModel):
    key = models.CharField(max_length=200)

    class Meta:
        db_table = 'webhook'
