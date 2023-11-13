from django.urls import path, include

app_name = 'v1'
urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('users/', include('users.urls')),
    path('', include('projects.urls')),
    path('', include('languages.urls')),
    path('', include('websites.urls')),
    path('', include('pages.urls')),
    path('', include('translations.urls')),
    path('payments/', include('payments.urls')),
    path('', include('commons.urls')),
    path('', include('website_redirects.urls')),
]
