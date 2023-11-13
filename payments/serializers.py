from rest_framework import serializers
from datetime import datetime
from payments.models import Subscription, SubscriptionPlan
from payments.stripe_services import (
    get_product_name_stripe,
    get_yearly_price_for_subscription,
)


class CheckoutSerializer(serializers.Serializer):
    price_id = serializers.CharField()
    page_name = serializers.CharField()


class PriceSerializer(serializers.Serializer):
    id = serializers.CharField()
    unit_amount = serializers.CharField()
    currency = serializers.CharField()


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    created = serializers.IntegerField()
    default_price = PriceSerializer()

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if (instance['name']).lower() in [
            SubscriptionPlan.FREE.name.lower(),
            SubscriptionPlan.STARTER.name.lower(),
            SubscriptionPlan.INDIVIDUAL.name.lower(),
            SubscriptionPlan.BUSINESS.name.lower(),
        ]:
            price = get_yearly_price_for_subscription(instance['id'])
            response['yearly_price'] = PriceSerializer(price).data
        return response


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            'plan',
            'period',
            'start_date',
            'end_date',
            'cancel_date',
            'status',
        )


class PaymentMethodCreateSerializer(serializers.Serializer):
    card_number = serializers.CharField()
    card_exp_month = serializers.IntegerField(min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(min_value=datetime.utcnow().year)
    card_cvc = serializers.CharField()


class PaymentMethodUpdateSerializer(serializers.Serializer):
    card_holder_name = serializers.CharField()
    card_exp_month = serializers.IntegerField(min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(min_value=datetime.utcnow().year)


class InvoiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    currency = serializers.CharField()
    invoice_pdf = serializers.CharField()

    def to_representation(self, instance):
        response = super().to_representation(instance)
        product_id = instance.lines.data[-1].price.product
        response['name'] = get_product_name_stripe(product_id=product_id)
        response['amount'] = abs(instance.total)
        response['created_at'] = instance.created
        return response
