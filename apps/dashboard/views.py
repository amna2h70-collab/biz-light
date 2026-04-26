from django.shortcuts import render
from .models import KPISnapshot
from .services import AnalyticsService
from automation.models import Alert

from django.contrib.auth.decorators import login_required
from inventory.models import Product

@login_required
def index(request):
    try:
        # Get latest snapshot
        latest_snapshot = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp').first()
        
        from django.utils import timezone
        now = timezone.now()
        forced_refresh = request.GET.get('refresh') == 'true'
        
        needs_auto_refresh = False
        if not latest_snapshot:
            needs_auto_refresh = True
        else:
            is_today = latest_snapshot.timestamp.date() == now.date()
            if not is_today and now.hour >= 9:
                needs_auto_refresh = True
                
        needs_refresh = forced_refresh or needs_auto_refresh
        
        if needs_refresh:
            try:
                latest_snapshot = AnalyticsService.calculate_kpis(request.user, force_new=forced_refresh, period='daily')
                # Clear AI summary on refresh to force new generation
                if forced_refresh and latest_snapshot:
                    KPISnapshot.objects.filter(id=latest_snapshot.id).update(ai_summary="")
                    latest_snapshot.ai_summary = ""
            except Exception as calc_err:
                print(f"KPI calculation failed in view: {calc_err}")
                # Fallback to existing snapshot if calculation fails
        
        if latest_snapshot and not latest_snapshot.ai_summary:
            try:
                from ai_layer.services import AIService
                ai_service = AIService()
                active_alerts = list(Alert.objects.filter(user_id=request.user.id, is_resolved__in=[False]).order_by('-timestamp')[:5])
                ai_summary_text = ai_service.generate_business_summary(
                    latest_snapshot, 
                    active_alerts
                )
                KPISnapshot.objects.filter(id=latest_snapshot.id).update(ai_summary=ai_summary_text)
                latest_snapshot.ai_summary = ai_summary_text
            except Exception as ai_err:
                print(f"AI Summary generation failed: {ai_err}")
                latest_snapshot.ai_summary = "AI analysis is currently being updated. Please check back in a moment."
                # Don't save the error message permanently, just show it
        
        # Get recent snapshots for charts (latest 1 per day for last 7 days)
        snapshots_qs = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp')
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
        
        # Get recent monthly snapshots (latest 1 per month for last 6 months)
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
        
        # Get active alerts for today only
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        alerts_qs = Alert.objects.filter(
            user_id=request.user.id, 
            is_resolved__in=[False],
            timestamp__gte=start_of_today
        ).order_by('-timestamp')
        alerts = list(alerts_qs[:5])
        
        # Get inventory products
        products = list(Product.objects.filter(user_id=request.user.id))
        
        # Get financial data for the last 6 months (Monthly) and last 14 days (Daily)
        from finance.models import Transaction, Expense
        import datetime
        
        now = timezone.now()
        six_months_ago = now - datetime.timedelta(days=180)
        fourteen_days_ago = now - datetime.timedelta(days=14)
        
        recent_sales = Transaction.objects.filter(user_id=request.user.id, type='SALE', timestamp__gte=six_months_ago)
        recent_expenses = Expense.objects.filter(user_id=request.user.id, date__gte=six_months_ago.date())
        
        monthly_summary = {}
        daily_summary = {}
        
        # Pre-fill last 6 months
        for i in range(5, -1, -1):
            m_date = (now.replace(day=1) - datetime.timedelta(days=i*30)).replace(day=1)
            month_key = m_date.strftime('%Y-%m')
            month_name = m_date.strftime('%b')
            monthly_summary[month_key] = {'label': month_name, 'revenue': 0, 'expenses': 0, 'cogs': 0, 'profit': 0}
            
        # Pre-fill last 14 days
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
                
            # Monthly
            m_key = sale.timestamp.strftime('%Y-%m')
            if m_key in monthly_summary:
                monthly_summary[m_key]['revenue'] += sale.total_amount
                monthly_summary[m_key]['cogs'] += cogs
                
            # Daily
            if sale.timestamp >= fourteen_days_ago:
                d_key = sale.timestamp.strftime('%Y-%m-%d')
                if d_key in daily_summary:
                    daily_summary[d_key]['revenue'] += sale.total_amount
                    daily_summary[d_key]['cogs'] += cogs
                
        for exp in recent_expenses:
            # Monthly
            m_key = exp.date.strftime('%Y-%m')
            if m_key in monthly_summary:
                monthly_summary[m_key]['expenses'] += exp.amount
                
            # Daily
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
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        latest_snapshot = None
        snapshots = []
        alerts = []
        products = []
        monthly_chart_data = []
        daily_chart_data = []
    
    context = {
        'snapshot': latest_snapshot,
        'snapshots': snapshots,  # Daily snapshots
        'monthly_snapshots': monthly_snapshots_list,
        'alerts': alerts,
        'products': products,
        'monthly_chart_data': monthly_chart_data,
        'daily_chart_data': daily_chart_data,
        'page_title': 'Business Overview'
    }
    return render(request, 'dashboard/index.html', context)

@login_required
def reports_list(request):
    if request.GET.get('generate') == 'true':
        try:
            from .services import AnalyticsService
            snapshot = AnalyticsService.calculate_kpis(request.user, force_new=True, period='daily')
            
            # Generate AI Summary
            from ai_layer.services import AIService
            ai_service = AIService()
            active_alerts = list(Alert.objects.filter(user_id=request.user.id, is_resolved__in=[False]).order_by('-timestamp')[:5])
            ai_summary_text = ai_service.generate_business_summary(
                snapshot, 
                active_alerts
            )
            KPISnapshot.objects.filter(id=snapshot.id).update(ai_summary=ai_summary_text)
            snapshot.ai_summary = ai_summary_text

        except Exception as e:
            import traceback
            print(f"Report generation failed: {e}")
            traceback.print_exc()
        from django.shortcuts import redirect
        return redirect('dashboard:reports')

    snapshots = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp')
    return render(request, 'dashboard/reports.html', {'snapshots': snapshots, 'page_title': 'Historical Reports'})
