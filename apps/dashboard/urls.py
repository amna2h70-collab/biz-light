from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('reports/', views.reports_list, name='reports'),
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    path('sync-store/', views.sync_store_data, name='sync_store'),
    path('integration/', views.integration_settings, name='integration'),
]
