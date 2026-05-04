from django.shortcuts import render, redirect
from django.contrib import messages
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
            is_resolved__in=[False]
        ).order_by('-timestamp')
        alerts = list(alerts_qs[:5])
        
        # Get inventory products
        products = list(Product.objects.filter(user_id=request.user.id))
        if not products:
            messages.info(request, "You have no products. Please add products to your inventory.")
        
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
        import traceback
        traceback.print_exc()
        messages.error(request, f"Dashboard error: {e}")
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


from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

@login_required
def export_pdf(request):
    snapshot = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp').first()
    template_path = 'dashboard/pdf_report.html'
    context = {'snapshot': snapshot, 'user': request.user}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="BizLight_Report.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

import requests
from finance.models import Transaction
from inventory.models import Product
from .models import StoreIntegration
from django.utils import timezone

@login_required
def integration_settings(request):
    integration, created = StoreIntegration.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        store_name = request.POST.get('store_name')
        platform_type = request.POST.get('platform_type', 'custom')
        store_url = request.POST.get('store_url')
        api_key = request.POST.get('api_key')
        
        if store_name and store_url and api_key:
            integration.store_name = store_name
            integration.platform_type = platform_type
            integration.store_url = store_url
            integration.api_key = api_key
            integration.save()
            messages.success(request, 'Store Integration settings saved successfully! Running initial sync...')
            return redirect('dashboard:sync_store')
        else:
            messages.error(request, 'Please fill in all fields.')
    
    platforms = StoreIntegration.PLATFORM_CHOICES
    return render(request, 'dashboard/integration.html', {'integration': integration, 'platforms': platforms})

@login_required
def sync_store_data(request):
    try:
        try:
            integration = StoreIntegration.objects.get(user=request.user)
            if not integration.store_url:
                raise StoreIntegration.DoesNotExist
        except StoreIntegration.DoesNotExist:
            messages.warning(request, "Please configure your Store Integration settings first.")
            return redirect('dashboard:integration')
        
        platform = integration.platform_type
        store_url = integration.store_url
        api_key = integration.api_key

        # ── Adapter: fetch orders based on platform ─────────────
        orders = []
        
        # Force IPv4 for Windows networking quirks
        active_url = store_url.replace('localhost', '127.0.0.1')
        
        if platform == 'custom':
            orders = _fetch_custom_orders(active_url)
            try:
                # Also fetch and create products if they don't exist
                products_url = active_url.replace('/orders', '/products')
                p_resp = requests.get(products_url, timeout=10)
                if p_resp.status_code == 200:
                    for sp in p_resp.json():
                        sku = sp.get('sku')
                        if sku:
                            Product.objects.get_or_create(
                                user_id=request.user.id,
                                sku=sku,
                                defaults={
                                    'name': sp.get('name', 'Unknown Product'),
                                    'price': sp.get('price', 0),
                                    'cost': float(sp.get('price', 0)) * 0.6,
                                    'stock_level': sp.get('stock', 0),
                                    'category': 'Synced Store'
                                }
                            )
            except Exception as pe:
                print(f"Product sync error: {pe}")
        elif platform == 'woocommerce':
            orders = _fetch_woocommerce_orders(store_url, api_key)
        elif platform == 'shopify':
            orders = _fetch_shopify_orders(store_url, api_key)
        elif platform == 'daraz':
            messages.info(request, "Daraz integration is coming soon.")
            return redirect('dashboard:index')
        
        # ── Process normalized orders ───────────────────────────
        synced_count = 0
        for order in orders:
            sku = order.get('sku')
            quantity = order.get('quantity', 1)
            try:
                product = Product.objects.get(sku=sku, user_id=request.user.id)
                total = product.price * quantity
                
                t = Transaction.objects.create(
                    user_id=request.user.id,
                    product=product,
                    type='SALE',
                    quantity=quantity,
                    total_amount=total
                )
                order_ts = order.get('timestamp')
                if order_ts:
                    from dateutil.parser import parse
                    t.timestamp = parse(order_ts)
                    t.save(update_fields=['timestamp'])
                Product.objects.filter(id=product.id).update(stock_level=product.stock_level - quantity)
                product.stock_level -= quantity
                
                # Mark order as synced (only for custom API)
                if platform == 'custom':
                    order_id = order.get('id')
                    requests.patch(f"{store_url}/{order_id}", json={"status": "Synced"})
                
                synced_count += 1
                
            except Product.DoesNotExist:
                continue
        
        if synced_count > 0:
            integration.last_synced = timezone.now()
            integration.save()
            from dashboard.services import AnalyticsService
            AnalyticsService.calculate_kpis(request.user)
            messages.success(request, f"Successfully pulled and synced {synced_count} new orders from {integration.get_platform_type_display()}!")
        else:
            messages.info(request, "No new pending orders found in the store database.")
    except Exception as e:
        messages.error(request, f"Sync connection error: {str(e)}")
        
    return redirect('dashboard:index')


# ─── Platform Adapters ──────────────────────────────────────────

def _fetch_custom_orders(store_url):
    """Adapter for Custom JSON Server API (WonderToyz)."""
    response = requests.get(store_url, timeout=10)
    response.raise_for_status()
    all_orders = response.json()
    return [o for o in all_orders if o.get('status') == 'Pending']


def _fetch_woocommerce_orders(store_url, api_key):
    """
    Adapter for WooCommerce REST API.
    store_url = base store URL, e.g. https://mystore.com
    api_key   = "consumer_key:consumer_secret" format
    """
    normalized = []
    
    # Parse consumer_key:consumer_secret from api_key field
    if ':' in api_key:
        consumer_key, consumer_secret = api_key.split(':', 1)
    else:
        consumer_key = api_key
        consumer_secret = ''
    
    # WooCommerce REST API v3 endpoint
    base = store_url.rstrip('/')
    url = f"{base}/wp-json/wc/v3/orders"
    params = {'status': 'processing', 'per_page': 50}
    
    response = requests.get(
        url,
        params=params,
        auth=(consumer_key, consumer_secret),
        timeout=15
    )
    response.raise_for_status()
    wc_orders = response.json()
    
    for wc_order in wc_orders:
        for item in wc_order.get('line_items', []):
            normalized.append({
                'id': wc_order.get('id'),
                'sku': item.get('sku', ''),
                'name': item.get('name', ''),
                'price': float(item.get('price', 0)),
                'quantity': item.get('quantity', 1),
                'status': 'Pending',
            })
    
    return normalized


def _fetch_shopify_orders(store_url, api_key):
    """
    Adapter for Shopify Admin REST API.
    store_url = e.g. https://mystore.myshopify.com
    api_key   = Shopify Admin API access token
    """
    normalized = []
    
    base = store_url.rstrip('/')
    url = f"{base}/admin/api/2024-01/orders.json"
    params = {'status': 'open', 'limit': 50}
    headers = {'X-Shopify-Access-Token': api_key}
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    shopify_data = response.json()
    
    for order in shopify_data.get('orders', []):
        for item in order.get('line_items', []):
            normalized.append({
                'id': order.get('id'),
                'sku': item.get('sku', ''),
                'name': item.get('title', ''),
                'price': float(item.get('price', 0)),
                'quantity': item.get('quantity', 1),
                'status': 'Pending',
            })
    
    return normalized

