import stripe
import logging
from rest_framework.exceptions import NotFound, APIException
from django.conf import settings

if settings.STRIPE_LIVE_MODE:
    stripe.api_key = settings.STRIPE_SECRET_KEY
else:
    stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


def get_price_by_id_stripe(price_id):
    price = stripe.Price.retrieve(
        id=price_id,
        expand=['product', 'recurring'],
    )
    if not price:
        raise NotFound(f'Not found price with id:{price_id}.')
    return price


def get_product_by_id_stripe(product_id):
    return stripe.Product.retrieve(id=product_id)


def get_customer_payment_methods_stripe(customer_id):
    return stripe.PaymentMethod.list(
        customer=customer_id,
        type='card',
    )


def get_customer_payment_method_stripe(customer_id, pm_id):
    return stripe.Customer.retrieve_payment_method(
        customer_id,
        pm_id,
    )


def create_payment_method_stripe(number, exp_month, exp_year, cvc):
    payment_method = stripe.PaymentMethod.create(
        type='card',
        card={
            'number': number,
            'exp_month': exp_month,
            'exp_year': exp_year,
            'cvc': cvc,
        },
    )
    return payment_method


def attach_payment_method_to_customer_stripe(pm_id, customer_id):
    return stripe.PaymentMethod.attach(
        pm_id,
        customer=customer_id,
    )


def update_customer_payment_method_stripe(id, card_holder_name, exp_month, exp_year):
    payment_method = stripe.PaymentMethod.modify(
        id,
        billing_details={'name': card_holder_name},
        card={
            'exp_month': exp_month,
            'exp_year': exp_year,
        },
    )
    return payment_method


def get_products_stripe():
    products = stripe.Product.search(
        expand=['data.default_price'],
        query="metadata['SUBSCRIPTION']:'subscriptions'",
    ).data
    return sorted(products, key=lambda x: x.default_price.unit_amount)


def get_credits_stripe():
    products = stripe.Product.search(
        expand=['data.default_price'], query="metadata['CREDITS']:'credits'"
    ).data
    return sorted(products, key=lambda x: x.created)


def get_customer_by_email_stripe(user_email):
    customer_data = stripe.Customer.list(email=user_email).data
    if len(customer_data) == 0:
        customer = stripe.Customer.create(email=user_email)
    else:
        customer = customer_data[0]
    return customer


def update_customer_account_in_stripe(user_email, email):
    customer = get_customer_by_email_stripe(user_email)
    if customer:
        stripe.Customer.modify(customer.id, email=email)


def get_customer_by_id(customer_id):
    customer = stripe.Customer.retrieve(id=customer_id)
    if not customer:
        raise NotFound(f'Not found customer with id:{customer_id}.')
    return customer


def get_customer_id_stripe(user_email):
    customer = get_customer_by_email_stripe(user_email)
    return customer.id


def get_prices_by_product_id_stripe(product_id):
    return stripe.Price.list(product=product_id).data


def get_yearly_price_for_subscription(product_id):
    prices = get_prices_by_product_id_stripe(product_id)
    for price in prices:
        if price.recurring.interval == 'year':
            return price


def create_checkout_session_stripe(customer_id, price, page_name):
    try:
        mode = 'payment' if price.type == 'one_time' else 'subscription'
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': price.id,
                    'quantity': 1,
                }
            ],
            mode=mode,
            success_url=f'{settings.FRONTEND_CHECKOUT_URL}{page_name}?status=success',
            cancel_url=f'{settings.FRONTEND_CHECKOUT_URL}{page_name}?status=failed',
            customer=customer_id,
            customer_update={'name': 'auto', 'address': 'auto'},
            billing_address_collection='required',
            automatic_tax={'enabled': True},
            tax_id_collection={
                'enabled': True,
            },
            invoice_creation={'enabled': True} if mode == 'payment' else None,
        )
        return checkout_session
    except Exception as e:
        logging.error(
            f'Failed to create checkout session for customer_id:{customer_id}! Error:{repr(e)}'
        )
        raise APIException(detail='Something went wrong in server.')


def get_product_name_stripe(product_id):
    product = get_product_by_id_stripe(product_id)
    return product.name if product else ''


def construct_event_in_webhook_stripe(payload, sig_header, webhook_secret_key):
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret_key)
    return event


def get_line_item_from_checkout_session_stripe(session_id):
    first_line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
    return first_line_items


def get_active_subscription_for_customer_stripe(customer_id):
    subscriptions = stripe.Subscription.list(customer=customer_id, status='active').data
    if len(subscriptions) > 0:
        return subscriptions[0]
    return None


def cancel_subscription_for_customer_stripe(subscription_id):
    subscription = stripe.Subscription.modify(
        subscription_id, cancel_at_period_end=True
    )
    if subscription.cancel_at_period_end:
        return True
    return False


def reactivate_canceled_subscription_for_customer_stripe(subscription_id):
    subscription = stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=False,
    )
    if subscription.cancel_at_period_end:
        return False
    return True


def upgrade_or_downgrade_subscription_for_customer_stripe(subscription, price_id):
    subscription = stripe.Subscription.modify(
        subscription.id,
        cancel_at_period_end=False,
        proration_behavior='always_invoice',
        items=[
            {
                'id': subscription['items']['data'][0].id,
                'price': price_id,
            }
        ],
    )
    if subscription:
        return True
    return False


def get_product_by_metadata_plan(plan):
    products = stripe.Product.search(
        query=f"metadata['PLAN']:'{plan}'",
    ).data
    if products:
        return products[0]
    else:
        return None


def get_customer_subscription_invoices_stripe(customer_id, page_size, cursor):
    return stripe.Invoice.list(
        customer=customer_id,
        status='paid',
        expand=['total_count'],
        limit=page_size,
        starting_after=cursor,
    )
