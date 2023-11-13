from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.services import check_users_expired_subscriptions
from users.models import UserCredits, UserFirebaseToken, UserProfile
from users.serializers import (
    UserCreditsCreateSerializer,
    UserCreditsSerializer,
    UserFirebaseTokenSerializer,
    UserProfileSerializer,
)
from rest_framework import parsers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from firebase.services import (
    delete_users_notifications_in_firebase_older_than_a_week_ago,
    update_unfinished_user_background_processes,
)


class UserCreditsViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserCreditsSerializer
    queryset = UserCredits.objects.all()
    lookup_field = 'guid'
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return UserCredits.objects.filter(user_id=self.request.user.id)

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreditsCreateSerializer
        return UserCreditsSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = UserCreditsSerializer(instance=serializer.instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.id)


class UserProfileViewSet(ModelViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.FileUploadParser,
    )
    http_method_names = ['post']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFirebaseTokenViewSet(ModelViewSet):
    serializer_class = UserFirebaseTokenSerializer
    queryset = UserFirebaseToken.objects.all()
    http_method_names = ['post']


@api_view(['POST'])
@permission_classes((AllowAny,))
def check_users_subscriptions(request):
    api_key = request.headers.get('api-key', '')
    check_users_expired_subscriptions(api_key)
    return HttpResponse(status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes((AllowAny,))
def delete_users_notifications_in_firebase(request):
    api_key = request.headers.get('api-key', '')
    delete_users_notifications_in_firebase_older_than_a_week_ago(api_key=api_key)
    return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes((AllowAny,))
def check_user_background_processes_in_firebase(request):
    api_key = request.headers.get('api-key', '')
    update_unfinished_user_background_processes(api_key=api_key)
    return HttpResponse(status=status.HTTP_200_OK)
