from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.list_products, name='list'),
    path('add/', views.add_product, name='add'),
    path('update-stock/<int:pk>/', views.update_stock, name='update_stock'),
]
