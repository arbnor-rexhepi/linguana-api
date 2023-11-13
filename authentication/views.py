from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.permissions import AllowAny
from allauth.account.admin import EmailAddress
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView, DestroyAPIView
from django.utils.translation import gettext_lazy as _
from authentication.serializers import ResendEmailVerificationSerializer
from users.models import User
from users.serializers import CustomUserSerializer
from rest_framework.exceptions import NotFound


class GoogleLoginAuthorization(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class ResendEmailVerificationView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResendEmailVerificationSerializer
    queryset = EmailAddress.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = EmailAddress.objects.filter(**serializer.validated_data).first()
        if email and not email.verified:
            email.send_confirmation(request)

        return Response({'detail': _('ok')}, status=status.HTTP_200_OK)


class DeleteUserAccountView(DestroyAPIView):
    serializer_class = CustomUserSerializer
    queryset = User.objects.all()

    def destroy(self, request):
        self.perform_destroy(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.delete()


class DeleteGoogleUserAccountView(DestroyAPIView):
    serializer_class = CustomUserSerializer
    queryset = User.objects.all()

    def destroy(self, request):
        user_social_account = request.user.socialaccount_set.filter(
            provider='google'
        ).first()
        if not user_social_account:
            raise NotFound('This user does not have a Google social account!')

        user_social_account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
