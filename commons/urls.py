from django.urls import path
from commons import views

app_name = 'commons'

urlpatterns = [
    path('maintenance/', views.maintenance, name='maintenance'),
]
