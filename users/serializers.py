from rest_framework import serializers
from payments.serializers import SubscriptionSerializer
from users.models import User, UserCredits, UserProfile, UserFirebaseToken
from payments.selectors import get_user_subscription
from users.services import (
    get_user_profile,
    update_or_create_user_firebase_token,
    update_or_create_user_profile,
)

from allauth.socialaccount.models import SocialAccount


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ('provider', 'last_login', 'date_joined')


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email',
            'guid',
            'remaining_credits',
            'verified_email',
            'email_confirmation_expire_days',
            'deactivated_account',
            'picture',
            'full_name',
            'type',
        )

    def to_representation(self, instance):
        response = super().to_representation(instance)
        subscription = get_user_subscription(instance.id)
        response['subscription'] = SubscriptionSerializer(subscription).data
        response['profile'] = UserProfileSerializer(get_user_profile(instance.id)).data
        response['social_account'] = SocialAccountSerializer(
            instance.socialaccount_set.all(), many=True
        ).data
        return response


class UserCreditsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCredits
        fields = (
            'guid',
            'user',
            'ai_credits',
        )


class UserCreditsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCredits
        fields = ('ai_credits',)


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, max_length=200, required=False)

    class Meta:
        model = UserProfile
        fields = ('firstname', 'email', 'lastname', 'picture')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['email'] = instance.user.email
        return response

    def create(self, validated_data):
        return update_or_create_user_profile(
            user=validated_data.get('user'),
            email=validated_data.get('email'),
            firstname=validated_data.get('firstname'),
            lastname=validated_data.get('lastname'),
            picture=validated_data.get('picture'),
            request=self.context.get('request'),
        )


class UserFirebaseTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFirebaseToken
        fields = ('token',)

    def create(self, validated_data):
        return update_or_create_user_firebase_token(
            user=self.context.get('request').user,
            token=validated_data.get('token'),
        )
