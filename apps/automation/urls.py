from django.urls import path
from . import views

app_name = 'automation'

urlpatterns = [
    path('alerts/', views.alert_list, name='alerts'),
    path('alerts/resolve/<int:pk>/', views.resolve_alert, name='resolve_alert'),
]
