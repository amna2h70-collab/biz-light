from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg
from finance.models import Transaction, Expense
from inventory.models import Product
from .models import KPISnapshot
from automation.models import Alert, ThresholdConfig


class AnalyticsService:
    @staticmethod
    def _get_threshold(user, key, default):
        """Get threshold from user config or use default."""
        try:
            config = ThresholdConfig.objects.filter(user_id=user.id, key=key).first()
            if config:
                return config.value
        except Exception:
            pass
        return default

    @staticmethod
    def calculate_kpis(user, force_new=False, period='daily'):
        now = timezone.now()
        
        if period == 'daily':
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_period_start = period_start - timedelta(days=1)
            days_in_period = 1
        elif period == 'weekly':
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
            prev_period_start = period_start - timedelta(days=7)
            days_in_period = 7
        else: # monthly
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_period_start = period_start - timedelta(days=30)
            days_in_period = 30

        # 1. Revenue Growth Rate (RGR)
        current_sales_data = Transaction.objects.filter(
            user_id=user.id, type='SALE', timestamp__gte=period_start, timestamp__lte=now
        ).values_list('total_amount', flat=True)
        current_sales = sum(current_sales_data)
        
        prev_sales_data = Transaction.objects.filter(
            user_id=user.id, type='SALE', timestamp__gte=prev_period_start, timestamp__lte=period_start
        ).values_list('total_amount', flat=True)
        prev_sales = sum(prev_sales_data)
        
        rgr = ((current_sales - prev_sales) / prev_sales) if prev_sales > 0 else 0

        # 2. Inventory Turnover Ratio (ITR)
        # COGS calculation (Manual for Djongo compatibility)
        sales = Transaction.objects.filter(user_id=user.id, type='SALE', timestamp__gte=period_start, timestamp__lte=now)
        cogs = 0
        for s in sales:
            try:
                # Access related fields carefully in Djongo
                cogs += (s.product.cost * s.quantity)
            except Exception:
                continue

        # Manual calculation for average inventory value (Djongo compatible)
        products = Product.objects.filter(user_id=user.id)
        product_data = list(products.values_list('stock_level', 'cost'))
        total_value = sum(level * cost for level, cost in product_data)
        avg_inventory_value = total_value / len(product_data) if len(product_data) > 0 else 1
        
        itr = float(cogs) / float(avg_inventory_value) if avg_inventory_value > 0 else 0

        # 3. Expense Ratio (ER)
        expense_data = Expense.objects.filter(
            user_id=user.id, date__gte=period_start.date(), date__lte=now.date()
        ).values_list('amount', flat=True)
        total_expenses = sum(expense_data)
        
        er = float(total_expenses) / float(current_sales) if current_sales > 0 else 0

        # 4. Stock Coverage Period (SCP)
        # total_stock calculation
        total_stock = sum(p[0] for p in product_data)
        
        # total_sales_qty calculation
        sales_qty_data = sales.values_list('quantity', flat=True)
        total_sales_qty = sum(sales_qty_data)
        
        avg_daily_sales_qty = float(total_sales_qty) / days_in_period
        scp = float(total_stock) / avg_daily_sales_qty if avg_daily_sales_qty > 0 else 999

        # 5. Business Health Score (BHS)
        rgr_norm = max(0, min(1, (rgr + 0.1) / 0.5))
        itr_norm = max(0, min(1, itr / 5))
        er_norm = max(0, min(1, er / 0.5))
        
        bhs = 0.4 * itr_norm + 0.35 * rgr_norm + 0.25 * (1 - er_norm)
        bhs = round(bhs * 100, 2)

        net_profit = current_sales - cogs - total_expenses
        
        # Find latest snapshot to see if we should update or create
        latest_snapshot = KPISnapshot.objects.filter(user_id=user.id).order_by('-timestamp').first()
        report_type_display = period.capitalize()
        
        if latest_snapshot and latest_snapshot.timestamp.date() == now.date() and not force_new:
            # Update today's snapshot
            KPISnapshot.objects.filter(id=latest_snapshot.id).update(
                rgr=rgr, itr=itr, er=er, scp=scp, bhs=bhs, ai_summary="", report_type=report_type_display,
                total_revenue=current_sales, total_expenses=total_expenses, net_profit=net_profit
            )
            latest_snapshot.rgr = rgr
            latest_snapshot.itr = itr
            latest_snapshot.er = er
            latest_snapshot.scp = scp
            latest_snapshot.bhs = bhs
            latest_snapshot.report_type = report_type_display
            latest_snapshot.ai_summary = ""
            latest_snapshot.total_revenue = current_sales
            latest_snapshot.total_expenses = total_expenses
            latest_snapshot.net_profit = net_profit
            snapshot = latest_snapshot
        else:
            # Create new snapshot
            snapshot = KPISnapshot.objects.create(
                user_id=user.id, rgr=rgr, itr=itr, er=er, scp=scp, bhs=bhs, report_type=report_type_display,
                total_revenue=current_sales, total_expenses=total_expenses, net_profit=net_profit
            )
        
        # Trigger Rule Engine
        AnalyticsService.run_rule_engine(user, snapshot)
        
        return snapshot

    @staticmethod
    def run_rule_engine(user, snapshot):
        """Complete rule-based evaluation per proposal requirements."""
        
        # --- Configurable thresholds ---
        scp_urgent_days = AnalyticsService._get_threshold(user, 'SCP_URGENT_DAYS', 3)
        itr_slow_threshold = AnalyticsService._get_threshold(user, 'ITR_SLOW_THRESHOLD', 1.5)
        er_spike_threshold = AnalyticsService._get_threshold(user, 'ER_SPIKE_THRESHOLD', 0.6)
        rgr_decline_threshold = AnalyticsService._get_threshold(user, 'RGR_DECLINE_THRESHOLD', -0.1)
        min_profit_margin = AnalyticsService._get_threshold(user, 'MIN_PROFIT_MARGIN', 0.20)

        products = list(Product.objects.filter(user_id=user.id))
        
        # Fetch all unresolved alerts once to avoid N+1 queries
        existing_alerts = list(Alert.objects.filter(user_id=user.id, is_resolved__in=[False]))

        # Rule 1: Low Stock Alerts
        for p in products:
            if p.stock_level <= p.reorder_point:
                already_exists = any(p.name in a.message and a.type == 'LOW_STOCK' for a in existing_alerts)
                if not already_exists:
                    Alert.objects.create(
                        user_id=user.id,
                        type='LOW_STOCK',
                        message=f"Stock low for {p.name} ({p.stock_level} left). Reorder recommended.",
                        severity='CRITICAL' if p.stock_level == 0 else 'HIGH' if p.stock_level <= p.reorder_point // 2 else 'MEDIUM',
                    )
            else:
                # Auto-resolve existing LOW_STOCK alerts if stock is now healthy
                for alert in existing_alerts:
                    if alert.type == 'LOW_STOCK' and p.name in alert.message:
                        Alert.objects.filter(id=alert.id).update(is_resolved=True)
                        alert.is_resolved = True

        # Rule 2: Urgent Reorder
        if snapshot.scp < scp_urgent_days and snapshot.scp != 999:
            already_exists = any(a.type == 'URGENT_REORDER' for a in existing_alerts)
            if not already_exists:
                Alert.objects.create(
                    user_id=user.id,
                    type='URGENT_REORDER',
                    message=f"Stock coverage is only {snapshot.scp:.1f} days. Urgent reorder recommended to avoid stockouts.",
                    severity='CRITICAL',
                )

        # Rule 3: Slow-Moving Inventory
        if snapshot.itr < itr_slow_threshold and snapshot.itr > 0:
            already_exists = any(a.type == 'SLOW_MOVING' for a in existing_alerts)
            if not already_exists:
                Alert.objects.create(
                    user_id=user.id,
                    type='SLOW_MOVING',
                    message=f"Inventory turnover is low ({snapshot.itr:.2f}x). Consider promotions or discounts to move slow-selling items.",
                    severity='MEDIUM',
                )

        # Rule 4: Expense Spike Warning
        if snapshot.er > er_spike_threshold:
            Alert.objects.create(
                user_id=user.id,
                type='EXPENSE_SPIKE',
                message=f"High expense ratio detected: {snapshot.er:.2%}. Review your recent spending to improve margins.",
                severity='HIGH',
            )

        # Rule 5: Sales Decline Alert
        if snapshot.rgr < rgr_decline_threshold:
            Alert.objects.create(
                user_id=user.id,
                type='SALES_DECLINE',
                message=f"Sales dropped by {abs(snapshot.rgr):.2%} compared to last period. Consider promotional strategies.",
                severity='MEDIUM',
            )

        # Rule 6: Pricing Recommendation
        for p in products:
            if p.price > 0 and p.cost > 0:
                margin = (p.price - p.cost) / p.price
                if margin < min_profit_margin:
                    already_exists = any(p.name in a.message and a.type == 'PRICING_ALERT' for a in existing_alerts)
                    if not already_exists:
                        suggested_price = p.cost / (1 - min_profit_margin)
                        Alert.objects.create(
                            user_id=user.id,
                            type='PRICING_ALERT',
                            message=f"Low margin on {p.name} ({margin:.0%}). Consider raising price from ${p.price:.2f} to ${suggested_price:.2f} for a {min_profit_margin:.0%} margin.",
                            severity='LOW',
                        )
