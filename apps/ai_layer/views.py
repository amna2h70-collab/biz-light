from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .services import AIService
import json


@csrf_exempt
@login_required
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)
            
            ai_service = AIService()
            if not ai_service.available:
                return JsonResponse({'response': "AI Chat is currently unavailable. Please check your API configuration."})
            
            # ── Build rich business context from the database ──
            context_parts = []
            
            from dashboard.models import KPISnapshot
            from inventory.models import Product
            from finance.models import Transaction, Expense
            from django.db.models import Sum, Count, F
            
            uid = request.user.id
            
            # 1. Full product catalog
            products = Product.objects.filter(user_id=uid)
            if products.count() > 0:
                product_lines = []
                for p in products:
                    product_lines.append(
                        f"  - {p.name} | SKU: {p.sku} | Price: PKR {p.price} | "
                        f"Cost: PKR {p.cost} | Stock: {p.stock_level} units | "
                        f"Reorder Point: {p.reorder_point}"
                    )
                context_parts.append(
                    f"PRODUCT CATALOG ({products.count()} items):\n" + "\n".join(product_lines)
                )
            else:
                context_parts.append("PRODUCT CATALOG: No products in inventory yet.")
            
            # 2. Per-product sales breakdown
            sales = (
                Transaction.objects.filter(user_id=uid, type='SALE')
                .values('product__name', 'product__sku')
                .annotate(
                    total_qty=Sum('quantity'),
                    total_revenue=Sum('total_amount'),
                    num_orders=Count('id')
                )
                .order_by('-total_revenue')
            )
            if sales:
                sales_lines = []
                for s in sales:
                    sales_lines.append(
                        f"  - {s['product__name']} ({s['product__sku']}): "
                        f"{s['total_qty']} units sold across {s['num_orders']} orders = "
                        f"PKR {s['total_revenue']}"
                    )
                context_parts.append(
                    f"SALES BREAKDOWN (ranked by revenue):\n" + "\n".join(sales_lines)
                )
            else:
                context_parts.append("SALES BREAKDOWN: No sales transactions recorded yet.")
            
            # 3. Aggregate financials
            total_rev = Transaction.objects.filter(user_id=uid, type='SALE').aggregate(
                total=Sum('total_amount'))['total'] or 0
            total_expenses = Expense.objects.filter(user_id=uid).aggregate(
                total=Sum('amount'))['total'] or 0
            net_profit = total_rev - total_expenses
            
            context_parts.append(
                f"FINANCIAL SUMMARY:\n"
                f"  - Total Revenue (all time): PKR {total_rev:,.0f}\n"
                f"  - Total Expenses (all time): PKR {total_expenses:,.0f}\n"
                f"  - Net Profit (all time): PKR {net_profit:,.0f}"
            )
            
            # 4. Latest KPI snapshot
            try:
                latest_kpi = KPISnapshot.objects.filter(
                    user_id=uid, report_type='Daily'
                ).latest('timestamp')
                context_parts.append(
                    f"LATEST DAILY KPI ({latest_kpi.timestamp.strftime('%Y-%m-%d')}):\n"
                    f"  - Business Health Score: {latest_kpi.bhs}/100\n"
                    f"  - Revenue Growth Rate: {latest_kpi.rgr_percentage:.1f}%\n"
                    f"  - Inventory Turnover: {latest_kpi.itr:.2f}x\n"
                    f"  - Expense Ratio: {latest_kpi.er_percentage:.1f}%\n"
                    f"  - Stock Coverage: {latest_kpi.scp:.0f} days\n"
                    f"  - Daily Revenue: PKR {latest_kpi.total_revenue:,.0f}\n"
                    f"  - Daily Net Profit: PKR {latest_kpi.net_profit:,.0f}"
                )
            except Exception:
                context_parts.append("LATEST DAILY KPI: No snapshots available yet.")
            
            # 5. Recent transactions (last 10)
            recent_txs = Transaction.objects.filter(user_id=uid).order_by('-timestamp')[:10]
            if recent_txs:
                tx_lines = []
                for t in recent_txs:
                    tx_lines.append(
                        f"  - [{t.timestamp.strftime('%Y-%m-%d')}] {t.type}: "
                        f"{t.product.name} x{t.quantity} = PKR {t.total_amount}"
                    )
                context_parts.append(
                    f"RECENT TRANSACTIONS (last {len(tx_lines)}):\n" + "\n".join(tx_lines)
                )
            
            full_context = "\n\n".join(context_parts)
            
            prompt = f"""You are Biz-Light Assistant, an expert AI business co-manager.
You have FULL ACCESS to the user's real business data shown below. Use it to answer their questions directly and accurately.

=== BUSINESS DATA START ===
{full_context}
=== BUSINESS DATA END ===

User question: {query}

CRITICAL RULES:
- ALWAYS answer using the ACTUAL data above. Never say "data is not available" if it IS in the data above.
- If they ask about products, list the actual product names from the catalog.
- If they ask about top sellers, use the SALES BREAKDOWN to rank them.
- If they ask about revenue or profit, use the FINANCIAL SUMMARY numbers.
- Be specific: use real product names, real PKR amounts, real quantities.
- Format responses with markdown: bold for emphasis, tables where helpful, bullet points for lists.
- Keep answers concise but data-rich. No fluff.
- If the data genuinely doesn't contain what they need, say so honestly but suggest next steps.
"""
            
            response_text = ai_service.generate_content(prompt)
            return JsonResponse({'response': response_text})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=405)
