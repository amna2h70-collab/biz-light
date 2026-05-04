import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.services import AnalyticsService
from dashboard.models import KPISnapshot

u = User.objects.get(email='ibrahim.urdux@gmail.com')
now = timezone.now()

# Delete existing to prevent duplicates
KPISnapshot.objects.filter(user=u, report_type='Daily').delete()

# Backfill
for i in range(14, -1, -1):
    d = now - datetime.timedelta(days=i)
    # Monkeypatch timezone.now for this calculation
    original_now = timezone.now
    timezone.now = lambda: d
    try:
        AnalyticsService.calculate_kpis(u, force_new=True, period='daily')
    finally:
        timezone.now = original_now

print('Backfilled 15 days of KPI snapshots')
