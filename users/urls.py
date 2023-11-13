from rest_framework.routers import DefaultRouter
from users.views import (
    UserCreditsViewSet,
    UserFirebaseTokenViewSet,
    UserProfileViewSet,
    check_users_subscriptions,
    delete_users_notifications_in_firebase,
    check_user_background_processes_in_firebase,
)
from django.urls import path, include


app_name = 'users'
router = DefaultRouter()
router.register(r'credits', UserCreditsViewSet)

profile_router = DefaultRouter()
profile_router.register(r'profile', UserProfileViewSet)

firebase_router = DefaultRouter()
firebase_router.register(r'firebase', UserFirebaseTokenViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('', include(profile_router.urls)),
    path('', include(firebase_router.urls)),
    path(
        'check-subscriptions/',
        check_users_subscriptions,
        name='check-users-subscriptions',
    ),
    path(
        'delete-notifications/',
        delete_users_notifications_in_firebase,
        name='delete-users-notifications-firebase',
    ),
    path(
        'check-background-processes/',
        check_user_background_processes_in_firebase,
        name='check-user-background-processes',
    ),
]
