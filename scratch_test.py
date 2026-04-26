import os
import django
from datetime import timedelta
import sys

# Ensure Django is set up
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

from django.contrib.auth.models import User
from apps.dashboard.services import AnalyticsService
from finance.models import Transaction, Expense
from apps.dashboard.models import KPISnapshot
from django.utils import timezone

def run():
    user = User.objects.first()
    now = timezone.now()
    
    start_date_fin = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sales_fin = sum(Transaction.objects.filter(user_id=user.id, type='SALE', timestamp__gte=start_date_fin).values_list('total_amount', flat=True)) or 0
    exps_fin = sum(Expense.objects.filter(user_id=user.id, date__gte=start_date_fin.date()).values_list('amount', flat=True)) or 0
    print(f'FINANCE: Sales: {sales_fin}, Exps: {exps_fin}')

    start_date_serv = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sales_serv = sum(Transaction.objects.filter(user_id=user.id, type='SALE', timestamp__range=(start_date_serv, now)).values_list('total_amount', flat=True)) or 0
    exps_serv = sum(Expense.objects.filter(user_id=user.id, date__gte=start_date_serv.date(), date__lte=now.date()).values_list('amount', flat=True)) or 0
    print(f'SERVICES (RANGE): Sales: {sales_serv}, Exps: {exps_serv}')
    
    latest_snap = KPISnapshot.objects.filter(user_id=user.id).order_by('-timestamp').first()
    print(f'LATEST SNAPSHOT ID {latest_snap.id}: Revenue={latest_snap.total_revenue}, Profit={latest_snap.net_profit}, Report Type={latest_snap.report_type}')

if __name__ == '__main__':
    run()
