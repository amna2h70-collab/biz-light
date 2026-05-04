import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.models import KPISnapshot
from automation.models import Alert
from inventory.models import Product
from finance.models import Transaction, Expense
import datetime

def test_index():
    users = User.objects.all()
    for user in users:
        print(f"Testing for user: {user.id}")
        try:
            latest_snapshot = KPISnapshot.objects.filter(user_id=user.id).order_by('-timestamp').first()
            
            now = timezone.now()
            forced_refresh = False
            
            needs_auto_refresh = False
            if not latest_snapshot:
                needs_auto_refresh = True
            else:
                is_today = latest_snapshot.timestamp.date() == now.date()
                if not is_today and now.hour >= 9:
                    needs_auto_refresh = True
                    
            needs_refresh = forced_refresh or needs_auto_refresh
            print(f"Needs refresh: {needs_refresh}")
            
            # we will skip the service call for a moment to see if the rest of the code works
            if latest_snapshot and not latest_snapshot.ai_summary:
                pass # skip AI service
                
            snapshots_qs = KPISnapshot.objects.filter(user_id=user.id).order_by('-timestamp')
            unique_daily_snapshots = []
            seen_dates = set()
            for s in snapshots_qs:
                date_str = s.timestamp.date().isoformat()
                if date_str not in seen_dates:
                    seen_dates.add(date_str)
                    unique_daily_snapshots.append(s)
                if len(unique_daily_snapshots) >= 7:
                    break
                    
            unique_daily_snapshots.reverse()
            snapshots = unique_daily_snapshots
            
            monthly_snapshots_list = []
            seen_months = set()
            for s in snapshots_qs:
                if s.report_type == 'Monthly' or s.report_type == 'monthly':
                    month_str = s.timestamp.strftime('%Y-%m')
                    if month_str not in seen_months:
                        seen_months.add(month_str)
                        monthly_snapshots_list.append(s)
                    if len(monthly_snapshots_list) >= 6:
                        break
            monthly_snapshots_list.reverse()
            
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            alerts_qs = Alert.objects.filter(
                user_id=user.id, 
                is_resolved__in=[False]
            ).order_by('-timestamp')
            alerts = list(alerts_qs[:5])
            
            products = list(Product.objects.filter(user_id=user.id))
            print(f"Products count: {len(products)}")
            
            six_months_ago = now - datetime.timedelta(days=180)
            fourteen_days_ago = now - datetime.timedelta(days=14)
            
            recent_sales = Transaction.objects.filter(user_id=user.id, type='SALE', timestamp__gte=six_months_ago)
            recent_expenses = Expense.objects.filter(user_id=user.id, date__gte=six_months_ago.date())
            
            monthly_summary = {}
            daily_summary = {}
            
            for i in range(5, -1, -1):
                m_date = (now.replace(day=1) - datetime.timedelta(days=i*30)).replace(day=1)
                month_key = m_date.strftime('%Y-%m')
                month_name = m_date.strftime('%b')
                monthly_summary[month_key] = {'label': month_name, 'revenue': 0, 'expenses': 0, 'cogs': 0, 'profit': 0}
                
            for i in range(13, -1, -1):
                d_date = now - datetime.timedelta(days=i)
                day_key = d_date.strftime('%Y-%m-%d')
                day_name = d_date.strftime('%b %d')
                daily_summary[day_key] = {'label': day_name, 'revenue': 0, 'expenses': 0, 'cogs': 0, 'profit': 0}
                
            for sale in recent_sales:
                cogs = 0
                try:
                    cogs = sale.quantity * sale.product.cost
                except Exception:
                    pass
                    
                m_key = sale.timestamp.strftime('%Y-%m')
                if m_key in monthly_summary:
                    monthly_summary[m_key]['revenue'] += sale.total_amount
                    monthly_summary[m_key]['cogs'] += cogs
                    
                if sale.timestamp >= fourteen_days_ago:
                    d_key = sale.timestamp.strftime('%Y-%m-%d')
                    if d_key in daily_summary:
                        daily_summary[d_key]['revenue'] += sale.total_amount
                        daily_summary[d_key]['cogs'] += cogs
                    
            for exp in recent_expenses:
                m_key = exp.date.strftime('%Y-%m')
                if m_key in monthly_summary:
                    monthly_summary[m_key]['expenses'] += exp.amount
                    
                if exp.date >= fourteen_days_ago.date():
                    d_key = exp.date.strftime('%Y-%m-%d')
                    if d_key in daily_summary:
                        daily_summary[d_key]['expenses'] += exp.amount
                    
            for key, data in monthly_summary.items():
                data['profit'] = data['revenue'] - data['cogs'] - data['expenses']
                
            for key, data in daily_summary.items():
                data['profit'] = data['revenue'] - data['cogs'] - data['expenses']
                
            monthly_chart_data = list(monthly_summary.values())
            daily_chart_data = list(daily_summary.values())
            print("Success!")
            
        except Exception as e:
            print(f"Dashboard error: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    test_index()
