from django.urls import path
from payments import views

urlpatterns = [
    path(
        r'subscriptions/',
        views.get_subscriptions,
        name='list_of_subscriptions',
    ),
    path(
        r'cancel-subscription/',
        views.cancel_subscription,
        name='cancel_subscription',
    ),
    path(
        r'reactivate-subscription/',
        views.reactivate_subscription,
        name='reactivate_subscription',
    ),
    path(
        r'credits/',
        views.get_credits,
        name='list_of_credits',
    ),
    path(
        r'checkout/',
        views.checkout,
        name='checkout',
    ),
    path(
        r'stripe_webhook/',
        views.stripe_webhook,
        name='stripe_webhook',
    ),
    path(r'payment-methods/', views.PaymentMethodList.as_view()),
    path(r'payment-methods/<str:id>/', views.PaymentMethodDetail.as_view()),
    path(r'invoices/', views.InvoiceList.as_view()),
]
