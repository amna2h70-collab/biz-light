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
        
        # NOTE: AI summary is now loaded asynchronously via /dashboard/ai-summary/
        # This prevents the Groq API call from blocking page load.

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
from django.utils import timezone
from fpdf import FPDF

class BusinessReportPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 24)
        self.set_text_color(14, 165, 233)
        self.cell(0, 10, 'Biz-Light AI Business Report', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(153, 153, 153)
        self.cell(0, 10, 'Generated by Biz-Light AI Co-Manager - Confidential', align='C')

@login_required
def export_pdf(request):
    snapshot = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp').first()
    
    pdf = BusinessReportPDF()
    pdf.add_page()
    
    # Subtitle
    pdf.set_font('helvetica', '', 14)
    pdf.set_text_color(102, 102, 102)
    date_str = timezone.now().strftime("%B %d, %Y")
    pdf.cell(0, 10, f'Prepared for {request.user.username} on {date_str}', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    if snapshot:
        # KPIs
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 10, "Key Performance Indicators", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        # Format KPIs
        bhs = f"{snapshot.bhs} / 100" if hasattr(snapshot, 'bhs') else "N/A"
        
        rgr_val = getattr(snapshot, 'rgr_percentage', 0)
        rgr = f"{rgr_val:.1f}%" if rgr_val is not None else "N/A"
        
        itr_val = getattr(snapshot, 'itr', 0)
        itr = f"{itr_val:.1f}x" if itr_val is not None else "N/A"
        
        scp_val = getattr(snapshot, 'scp', 0)
        scp = f"{scp_val:.0f} days" if scp_val is not None else "N/A"

        kpis = [
            ("Business Health Score", bhs),
            ("Revenue Growth Rate", rgr),
            ("Inventory Turnover", itr),
            ("Stock Coverage Period", scp)
        ]
        
        for title, value in kpis:
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(102, 102, 102)
            pdf.cell(90, 6, title.upper(), border=0)
            
            pdf.set_font("helvetica", "B", 16)
            pdf.set_text_color(17, 17, 17)
            pdf.cell(90, 6, value, border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
        pdf.ln(10)
        pdf.set_draw_color(221, 221, 221)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(3, 105, 161)
        pdf.cell(0, 10, "AI Strategic Insight", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        if hasattr(snapshot, 'ai_summary') and snapshot.ai_summary:
            pdf.set_font("helvetica", "", 12)
            pdf.set_text_color(51, 51, 51)
            try:
                pdf.write_html(snapshot.ai_summary)
            except Exception as e:
                print("Failed to write HTML to PDF:", e)
                import re
                clean_text = re.sub('<[^<]+>', '', snapshot.ai_summary)
                pdf.multi_cell(0, 6, clean_text)
    else:
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(51, 51, 51)
        pdf.multi_cell(0, 10, "No data available to generate report. Please ensure your dashboard has generated a snapshot.")
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="BizLight_Report.pdf"'
    
    pdf_bytes = bytearray(pdf.output())
    response.write(pdf_bytes)
    
    return response


@login_required
def fetch_ai_summary(request):
    """
    Async endpoint: called by JS on page load to load the AI summary without
    blocking the dashboard render.  Returns JSON with the generated HTML.
    """
    from django.http import JsonResponse as _JsonResponse
    try:
        snapshot = KPISnapshot.objects.filter(user_id=request.user.id).order_by('-timestamp').first()
        if not snapshot:
            return _JsonResponse({'html': '<p class="text-zinc-400">No business data yet. Add products and log some sales to generate your AI summary.</p>'})

        # Return cached summary if it already exists
        if snapshot.ai_summary:
            return _JsonResponse({'html': snapshot.ai_summary})

        # Generate fresh summary
        from ai_layer.services import AIService
        ai_service = AIService()
        active_alerts = list(Alert.objects.filter(user_id=request.user.id, is_resolved__in=[False]).order_by('-timestamp')[:5])
        ai_summary_text = ai_service.generate_business_summary(snapshot, active_alerts)
        KPISnapshot.objects.filter(id=snapshot.id).update(ai_summary=ai_summary_text)
        return _JsonResponse({'html': ai_summary_text})
    except Exception as e:
        return _JsonResponse({'html': f'<p class="text-zinc-400">AI analysis is temporarily unavailable.</p>'}, status=200)

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
            orders = _fetch_shopify_orders(store_url, api_key, user=request.user)
        
        # ── Process normalized orders ───────────────────────────
        synced_count = 0
        for order in orders:
            sku = order.get('sku')
            quantity = order.get('quantity', 1)
            order_ts = order.get('timestamp')
            
            try:
                product = Product.objects.get(sku=sku, user_id=request.user.id)
                total = product.price * quantity
                
                parsed_ts = None
                if order_ts:
                    from dateutil.parser import parse
                    parsed_ts = parse(order_ts)
                    # Deduplication: check if this specific order is already recorded
                    if Transaction.objects.filter(
                        user_id=request.user.id,
                        product=product,
                        type='SALE',
                        quantity=quantity,
                        timestamp=parsed_ts
                    ).exists():
                        continue  # Skip already synced order
                
                t = Transaction.objects.create(
                    user_id=request.user.id,
                    product=product,
                    type='SALE',
                    quantity=quantity,
                    total_amount=total
                )
                
                if parsed_ts:
                    t.timestamp = parsed_ts
                    t.save(update_fields=['timestamp'])
                    
                product.stock_level -= quantity
                product.save(update_fields=['stock_level'])
                
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
    # Return all orders instead of filtering by 'Pending'. 
    # Deduplication is handled gracefully in the sync loop.
    return all_orders


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


def _fetch_shopify_orders(store_url, api_key, user=None):
    """
    Adapter for Shopify Admin REST API.
    store_url = e.g. https://mystore.myshopify.com
    api_key   = Shopify Admin API access token

    DEMO / VIVA MODE:
    Set api_key to 'mock' (or include 'mock' in the store URL) to run a
    simulation without a real Shopify store.  The adapter will return one
    synthetic order per product already in the user's inventory so the sync
    flow can be demonstrated end-to-end during evaluation.
    """
    # ── Mock / demo mode ─────────────────────────────────────────
    if api_key.strip().lower() == 'mock' or 'mock' in store_url.lower():
        normalized = []
        if user is not None:
            from inventory.models import Product as _Product
            from django.utils import timezone as _tz
            import datetime as _dt

            products = list(_Product.objects.filter(user_id=user.id))
            mock_ts = (_tz.now() - _dt.timedelta(hours=1)).isoformat()
            for p in products:
                if p.stock_level > 0:          # only sell items that are in stock
                    normalized.append({
                        'id': f'mock_{p.sku}',
                        'sku': p.sku,
                        'name': p.name,
                        'price': p.price,
                        'quantity': 1,
                        'status': 'Pending',
                        'timestamp': mock_ts,
                    })
        return normalized

    # ── Live Shopify Admin REST API ───────────────────────────────
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
                'timestamp': order.get('created_at', ''),
            })

    return normalized

