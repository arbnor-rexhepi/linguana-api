from payments.models import (
    ProductType,
    Subscription,
    SubscriptionPeriod,
    SubscriptionPlan,
    SubscriptionStatus,
    Webhook,
)
from payments.selectors import get_user_subscription
from projects.services import enable_user_disabled_projects_and_website_versions
from users.models import UserCreditsSource, UserType
from users.services import add_user_ai_credits, get_user_by_email
from django.db import transaction
import logging
from rest_framework.exceptions import ValidationError, APIException, NotFound
from datetime import datetime
from django.utils import timezone
from payments.stripe_services import (
    attach_payment_method_to_customer_stripe,
    cancel_subscription_for_customer_stripe,
    construct_event_in_webhook_stripe,
    create_checkout_session_stripe,
    create_payment_method_stripe,
    get_active_subscription_for_customer_stripe,
    get_credits_stripe,
    get_customer_by_email_stripe,
    get_customer_by_id,
    get_customer_id_stripe,
    get_customer_payment_method_stripe,
    get_customer_payment_methods_stripe,
    get_customer_subscription_invoices_stripe,
    get_line_item_from_checkout_session_stripe,
    get_price_by_id_stripe,
    get_product_by_metadata_plan,
    get_products_stripe,
    reactivate_canceled_subscription_for_customer_stripe,
    update_customer_payment_method_stripe,
    upgrade_or_downgrade_subscription_for_customer_stripe,
)
from websites.services import create_or_update_multiple_user_website_settings
from app.external_services.mailerlite_services import (
    update_mailer_lite_user_subscription,
)


def get_products_and_prices():
    return get_products_stripe()


def get_credits_and_prices():
    return get_credits_stripe()


def update_or_create_subscription(
    user_id,
    subscription_plan,
    subscription_period,
    start_date,
    end_date,
    cancel_date,
    status,
):
    obj, _ = Subscription.objects.update_or_create(
        user_id=user_id,
        defaults={
            'plan': subscription_plan,
            'period': subscription_period,
            'start_date': start_date,
            'end_date': end_date,
            'cancel_date': cancel_date,
            'status': status,
        },
    )
    return obj


def get_new_subscription_plan(plan):
    if plan == SubscriptionPlan.BUSINESS.name.upper():
        return SubscriptionPlan.BUSINESS
    elif plan == SubscriptionPlan.INDIVIDUAL.name.upper():
        return SubscriptionPlan.INDIVIDUAL
    elif plan == SubscriptionPlan.STARTER.name.upper():
        return SubscriptionPlan.STARTER
    else:
        return SubscriptionPlan.FREE


def create_checkout_session(user, price_id, page_name):
    try:
        checkout_session_created = False
        checkout_session = None
        is_upgrade_or_downgrade_subscription = False
        customer = get_customer_by_email_stripe(user.email)

        price = get_price_by_id_stripe(price_id)
        subscription = get_active_subscription_for_customer_stripe(customer.id)
        if price.unit_amount < 1:
            if subscription:
                cancel_subscription_for_customer_stripe(subscription.id)
            is_upgrade_or_downgrade_subscription = True
            return (
                checkout_session_created,
                checkout_session,
                is_upgrade_or_downgrade_subscription,
            )

        if not subscription or ProductType.CREDITS.name in price.product.metadata:
            checkout_session = create_checkout_session_stripe(
                customer.id, price, page_name
            )
            checkout_session_created = True
            return (
                checkout_session_created,
                checkout_session,
                is_upgrade_or_downgrade_subscription,
            )

        is_upgrade_or_downgrade_subscription = (
            upgrade_or_downgrade_subscription_for_customer_stripe(
                subscription, price_id
            )
        )
        return (
            checkout_session_created,
            checkout_session,
            is_upgrade_or_downgrade_subscription,
        )
    except Exception as e:
        logging.error(
            f'Failed to create checkout_session for price_id:{price_id}, user_email:{user.email}! Error:{repr(e)}'
        )
        raise APIException(detail='Something went wrong in server, please try again!')


def cancel_user_subscription(user):
    try:
        customer_id = get_customer_id_stripe(user.email)
        subscription = get_active_subscription_for_customer_stripe(customer_id)
        if not subscription:
            raise ValidationError('You do not have an active subscription!')
        return cancel_subscription_for_customer_stripe(subscription['id'])
    except Exception as e:
        if isinstance(e, ValidationError):
            raise e
        logging.error(
            f'Failed to cancel subscription with id:{subscription.id}, user_email:{user.email}! Error:{repr(e)}'
        )
        raise APIException(detail='Something went wrong in server, please try again!')


def reactivate_user_subscription(user):
    try:
        customer_id = get_customer_id_stripe(user.email)
        subscription = get_active_subscription_for_customer_stripe(customer_id)
        if not subscription:
            raise ValidationError('Your subscription has expired.')
        if not subscription.cancel_at_period_end:
            raise ValidationError('You already have an active subscription.')
        return reactivate_canceled_subscription_for_customer_stripe(subscription['id'])
    except Exception as e:
        logging.error(
            f'Failed to reactivate subscription with id:{subscription.id}, user_email:{user.email}! Error:{repr(e)}'
        )
        raise APIException(detail='Something went wrong in server, please try again!')


def save_ai_credits_in_db(customer_id, price_id):
    try:
        customer = get_customer_by_id(customer_id)
        user = get_user_by_email(customer.email)
        price = get_price_by_id_stripe(price_id)
        product = price.product
        credits = int(product.metadata.QUANTITY)
        add_user_ai_credits(
            user.id, ai_credits=credits, source=UserCreditsSource.CREDITS
        )
        return True
    except Exception as e:
        logging.error(
            f'Failed to save ai_credits customer_id:{customer_id}, price_id:{price_id}! Error:{repr(e)}'
        )
        return False


@transaction.atomic()
def save_subscription_data_in_db(
    customer_id,
    price_id,
    start_date,
    end_date,
    cancel_date,
    status,
    is_created_sub=False,
):
    try:
        customer = get_customer_by_id(customer_id)
        user = get_user_by_email(customer.email)
        if not user:
            logging.error(f'Does not exist any user with email:{customer.email}')
            return False
        price = get_price_by_id_stripe(price_id)
        product = price.product
        price_period = price.recurring.interval
        subscription_period = get_subscription_period(price_period)
        new_sub_plan = get_new_subscription_plan(product.metadata.PLAN)
        credits = int(product.metadata.QUANTITY)

        if status == SubscriptionStatus.CANCELED:
            new_sub_plan = SubscriptionPlan.FREE

        if new_sub_plan != SubscriptionPlan.FREE and is_created_sub:
            add_user_ai_credits(
                user.id, ai_credits=credits, source=UserCreditsSource.SUBSCRIPTION
            )
        subscription = get_user_subscription(user_id=user.id)
        if not is_created_sub and status != SubscriptionStatus.CANCELED:
            if check_if_user_downgrade_subscription(
                user=user, current_sub_plan=subscription.plan, new_sub_plan=new_sub_plan
            ):
                status = SubscriptionStatus.DOWNGRADED
            elif check_if_user_upgrade_subscription(
                user=user, current_sub_plan=subscription.plan, new_sub_plan=new_sub_plan
            ):
                status = SubscriptionStatus.UPGRADED
                product = get_product_by_metadata_plan(plan=subscription.plan)
                if product:
                    ai_credits = int(product.metadata.QUANTITY)
                    differences_of_ai_credits = credits - ai_credits
                    add_user_ai_credits(
                        user.id,
                        ai_credits=differences_of_ai_credits,
                        source=UserCreditsSource.SUBSCRIPTION,
                    )
                enable_user_disabled_projects_and_website_versions(
                    user=user, sub_plan=new_sub_plan
                )

            else:
                status = status

        update_or_create_subscription(
            user_id=user.id,
            subscription_plan=new_sub_plan,
            subscription_period=subscription_period,
            start_date=start_date,
            end_date=end_date,
            cancel_date=cancel_date,
            status=status,
        )

        show_badge = (
            new_sub_plan == SubscriptionPlan.FREE and user.type == UserType.FREE
        )
        create_or_update_multiple_user_website_settings(user.id, show_badge=show_badge)

        update_mailer_lite_user_subscription(user.email, status)

        return True
    except Exception as e:
        logging.error(
            f'Failed to save subscription data in db customer_id:{customer_id}, price_id:{price_id}! Error:{repr(e)}'
        )
        return False


def check_if_user_upgrade_subscription(user, current_sub_plan, new_sub_plan):
    if (
        current_sub_plan == SubscriptionPlan.STARTER
        and new_sub_plan in [SubscriptionPlan.INDIVIDUAL, SubscriptionPlan.BUSINESS]
    ) or (
        current_sub_plan == SubscriptionPlan.INDIVIDUAL
        and new_sub_plan == SubscriptionPlan.BUSINESS
    ):
        logging.info(
            f'User with email:{user.email} has upgrade subscription from {current_sub_plan} to {new_sub_plan}'
        )
        return True
    return False


def check_if_user_downgrade_subscription(user, current_sub_plan, new_sub_plan):
    if (
        current_sub_plan == SubscriptionPlan.BUSINESS
        and new_sub_plan
        in [
            SubscriptionPlan.INDIVIDUAL,
            SubscriptionPlan.STARTER,
        ]
    ) or (
        current_sub_plan == SubscriptionPlan.INDIVIDUAL
        and new_sub_plan == SubscriptionPlan.STARTER
    ):
        logging.info(
            f'User with email:{user.email} has downgrade subscription from {current_sub_plan} to {new_sub_plan}'
        )
        return True
    return False


def get_subscription_period(subscription_period):
    if subscription_period == 'year':
        return SubscriptionPeriod.YEARLY
    return SubscriptionPeriod.MONTHLY


def handle_event_that_stripe_sent_in_webhook(payload, sig_header):
    event = None
    try:
        try:
            webhook_secret_key = get_webhook_key()
            event = construct_event_in_webhook_stripe(
                payload, sig_header, webhook_secret_key
            )
        except Exception as e:
            logging.error(f'Invalid payload! Error:{repr(e)}')
            return False

        # Handle the event
        if event.type == 'checkout.session.completed':
            checkout_session = event.data.object
            line_item = get_line_item_from_checkout_session_stripe(checkout_session.id)
            customer_id = checkout_session.customer
            price_id = line_item.data[0].price.id
            if customer_id is None or price_id is None:
                logging.error(
                    f"""
                                The data for session with id:{checkout_session.id}
                                customer_id:{customer_id}, price_id:{price_id} could not be saved!
                            """
                )
                return None
            if checkout_session.payment_intent:
                save_ai_credits_in_db(customer_id, price_id)
            else:
                logging.info(f'Unknown this checkout_session:{checkout_session.id}!')
        elif event.type == 'customer.subscription.created':
            subscription = event.data.object
            (
                customer_id,
                price_id,
                start_date,
                end_date,
                cancel_date,
                status,
            ) = get_subscription_properties(subscription)
            if customer_id is None or price_id is None:
                logging.error(
                    f"""
                                The data for subscription with id:{subscription.id}
                                customer_id:{customer_id}, price_id:{price_id} could not be saved!
                            """
                )
                return None
            save_subscription_data_in_db(
                customer_id,
                price_id,
                start_date,
                end_date,
                cancel_date,
                status,
                is_created_sub=True,
            )
        elif event.type == 'customer.subscription.updated':
            subscription = event.data.object
            (
                customer_id,
                price_id,
                start_date,
                end_date,
                cancel_date,
                status,
            ) = get_subscription_properties(subscription)
            if customer_id is None or price_id is None:
                logging.error(
                    f"""
                                The data for subscription with id:{subscription.id}
                                customer_id:{customer_id}, price_id:{price_id} could not be saved!
                            """
                )
                return None
            save_subscription_data_in_db(
                customer_id,
                price_id,
                start_date,
                end_date,
                cancel_date,
                status,
            )
        else:
            print('Unhandled event type {}'.format(event.type))
        return True
    except Exception as e:
        logging.error(f'Failed to handle events from stripe! Error:{repr(e)}')
        return False


def get_subscription_properties(subscription):
    customer_id = subscription.customer
    price_id = subscription['items']['data'][0]['price'].id
    start_date = convert_timestamp_to_utc_date_time(subscription.current_period_start)
    end_date = convert_timestamp_to_utc_date_time(subscription.current_period_end)
    cancel_date = convert_timestamp_to_utc_date_time(subscription.canceled_at)
    if subscription.cancel_at_period_end:
        status = SubscriptionStatus.CANCELED
    else:
        status = SubscriptionStatus.ACTIVE
    return customer_id, price_id, start_date, end_date, cancel_date, status


def convert_timestamp_to_utc_date_time(timestamp):
    if timestamp is None:
        return None
    date_time = datetime.utcfromtimestamp(timestamp).replace(tzinfo=timezone.utc)
    return str(date_time)


def get_webhook_key():
    webhook = Webhook.objects.last()
    return webhook.key


def get_user_payment_methods(user):
    customer = get_customer_by_email_stripe(user_email=user.email)
    payment_methods = get_customer_payment_methods_stripe(customer_id=customer.id)
    return map(map_payment_method, payment_methods)


def get_user_payment_method(user, id):
    customer = get_customer_by_email_stripe(user_email=user.email)
    payment_method = get_customer_payment_method_stripe(
        customer_id=customer.id, pm_id=id
    )
    return map_payment_method(payment_method=payment_method)


def create_user_payment_method(user, number, exp_month, exp_year, cvc):
    customer = get_customer_by_email_stripe(user_email=user.email)
    payment_method = create_payment_method_stripe(
        number=number,
        exp_month=exp_month,
        exp_year=exp_year,
        cvc=cvc,
    )
    payment_method = attach_payment_method_to_customer_stripe(
        pm_id=payment_method.id, customer_id=customer.id
    )
    return map_payment_method(payment_method=payment_method)


def update_user_payment_method(user, pm_id, card_holder_name, exp_month, exp_year):
    customer = get_customer_by_email_stripe(user_email=user.email)
    payment_method = get_customer_payment_method_stripe(
        customer_id=customer.id, pm_id=pm_id
    )
    if not payment_method:
        raise NotFound(
            f'Not found payment method with id:{pm_id} for user:{user.email}!'
        )
    payment_method = update_customer_payment_method_stripe(
        id=payment_method.id,
        card_holder_name=card_holder_name,
        exp_month=exp_month,
        exp_year=exp_year,
    )
    return map_payment_method(payment_method=payment_method)


def map_payment_method(payment_method):
    return {
        'id': payment_method.id,
        'card_holder_name': payment_method.billing_details.name or '',
        'card_last4_number': payment_method.card.last4,
        'card_exp_month': payment_method.card.exp_month,
        'card_exp_year': payment_method.card.exp_year,
    }


def get_user_invoices(user, page_size, cursor):
    customer = get_customer_by_email_stripe(user_email=user.email)
    invoices = get_customer_subscription_invoices_stripe(
        customer_id=customer.id,
        page_size=page_size,
        cursor=cursor,
    )
    return invoices
