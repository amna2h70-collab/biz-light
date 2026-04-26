from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls', namespace='accounts')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('automation/', include('automation.urls', namespace='automation')),
    path('ai/', include('ai_layer.urls', namespace='ai_layer')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
