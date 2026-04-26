from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.transaction_list, name='transactions'),
    path('log-sale/', views.log_sale, name='log_sale'),
    path('log-expense/', views.log_expense, name='log_expense'),
    path('api/webhook/sale/', views.webhook_sale, name='webhook_sale'),
]
