from rest_framework import status
from rest_framework.response import Response
from payments.paginations import CustomPagination
from payments.serializers import (
    CheckoutSerializer,
    InvoiceSerializer,
    PaymentMethodCreateSerializer,
    PaymentMethodUpdateSerializer,
    ProductSerializer,
)
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from payments.services import (
    cancel_user_subscription,
    create_user_payment_method,
    get_products_and_prices,
    get_credits_and_prices,
    create_checkout_session,
    get_user_invoices,
    get_user_payment_method,
    get_user_payment_methods,
    handle_event_that_stripe_sent_in_webhook,
    reactivate_user_subscription,
    update_user_payment_method,
)
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from rest_framework import generics


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_subscriptions(request):
    products = get_products_and_prices()
    serializer = ProductSerializer(data=products, many=True)
    serializer.is_valid(raise_exception=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def get_credits(request):
    products = get_credits_and_prices()
    serializer = ProductSerializer(data=products, many=True)
    serializer.is_valid(raise_exception=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='POST', request_body=CheckoutSerializer)
@api_view(['POST'])
@permission_classes((IsAuthenticated,))
@csrf_exempt
def checkout(request):
    user = request.user
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    price_id = serializer.data.get('price_id')
    page_name = serializer.data.get('page_name')
    (
        checkout_session_created,
        checkout_session,
        is_upgrade_or_downgrade_subscription,
    ) = create_checkout_session(user, price_id, page_name)
    return Response(
        data={
            'checkout_session_created': checkout_session_created,
            'checkout_session_url': checkout_session.url
            if checkout_session_created
            else None,
            'is_upgrade_or_downgrade_subscription': is_upgrade_or_downgrade_subscription,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def cancel_subscription(request):
    user = request.user
    is_canceled_subscription = cancel_user_subscription(user)
    return Response(
        data={'is_canceled_subscription': is_canceled_subscription},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def reactivate_subscription(request):
    user = request.user
    is_reactivated_subscription = reactivate_user_subscription(user)
    return Response(
        data={'is_reactivated_subscription': is_reactivated_subscription},
        status=status.HTTP_200_OK,
    )


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = handle_event_that_stripe_sent_in_webhook(payload, sig_header)
    if not event:
        logging.error('No event has triggered!')
        return HttpResponse(status=400)
    return HttpResponse(status=200)


class InvoiceList(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    pagination_class = CustomPagination

    def get(self, request):
        cursor = self.request.query_params.get('cursor', None)
        page_size = int(self.request.query_params.get('page_size', 10))
        invoices = get_user_invoices(
            user=request.user, page_size=page_size, cursor=cursor
        )
        serializer = InvoiceSerializer(invoices.data, many=True)
        return Response(
            data={
                'total_count': invoices.total_count,
                'has_more': invoices.has_more,
                'data': serializer.data,
            }
        )


class PaymentMethodList(generics.ListCreateAPIView):
    serializer_class = PaymentMethodCreateSerializer

    def get(self, request, format=None):
        payment_methods = get_user_payment_methods(user=request.user)
        return Response(payment_methods)

    def post(self, request, format=None):
        data = request.data
        PaymentMethodCreateSerializer(data=data).is_valid(raise_exception=True)
        payment_method = create_user_payment_method(
            user=request.user,
            number=data.get('card_number'),
            exp_month=data.get('card_exp_month'),
            exp_year=data.get('card_exp_year'),
            cvc=data.get('card_cvc'),
        )
        return Response(data=payment_method, status=status.HTTP_201_CREATED)


class PaymentMethodDetail(generics.RetrieveUpdateAPIView):
    serializer_class = PaymentMethodUpdateSerializer

    def get(self, request, id):
        payment_method = get_user_payment_method(user=request.user, id=id)
        return Response(data=payment_method, status=status.HTTP_200_OK)

    def put(self, request, id):
        data = request.data
        payment_method = update_user_payment_method(
            user=request.user,
            pm_id=id,
            card_holder_name=data.get('card_holder_name'),
            exp_month=data.get('card_exp_month'),
            exp_year=data.get('card_exp_year'),
        )
        return Response(data=payment_method, status=status.HTTP_200_OK)

    @swagger_auto_schema(auto_schema=None)
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
