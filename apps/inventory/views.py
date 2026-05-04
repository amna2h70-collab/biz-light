from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product
from django.contrib import messages
from automation.models import Alert
from dashboard.services import AnalyticsService


def _resolve_alerts_for_product(user, product):
    """Auto-resolve LOW_STOCK alerts when stock goes above reorder point."""
    if product.stock_level > product.reorder_point:
        # Find all unresolved LOW_STOCK alerts mentioning this product
        unresolved = Alert.objects.filter(
            user_id=user.id,
            type='LOW_STOCK',
            is_resolved__in=[False]
        )
        # Filter alerts that mention this product's name
        for alert in unresolved:
            if product.name in alert.message:
                alert.is_resolved = True
                alert.save()


def _create_low_stock_alert(user, product):
    """Create a LOW_STOCK alert if stock is at or below reorder point."""
    if product.stock_level <= product.reorder_point:
        # Check if there's already an unresolved alert for this product
        existing = list(Alert.objects.filter(
            user_id=user.id,
            type='LOW_STOCK',
            is_resolved__in=[False]
        ))
        already_exists = any(product.name in a.message for a in existing)
        if not already_exists:
            Alert.objects.create(
                user_id=user.id,
                type='LOW_STOCK',
                message=f"Stock low for {product.name} ({product.stock_level} left). Reorder recommended.",
                severity='CRITICAL' if product.stock_level == 0 else 'HIGH' if product.stock_level <= product.reorder_point // 2 else 'MEDIUM',
            )


@login_required
def list_products(request):
    products = Product.objects.filter(user_id=request.user.id).order_by('name')
    return render(request, 'inventory/list.html', {'products': products, 'page_title': 'Inventory Management'})


@login_required
def add_product(request):
    if request.method == 'POST':
        try:
            sku = request.POST['sku']
            # Check if SKU already exists for this user
            if Product.objects.filter(user_id=request.user.id, sku=sku).exists():
                messages.error(request, f"Product with SKU '{sku}' already exists.")
                return redirect('inventory:list')

            product = Product.objects.create(
                user_id=request.user.id,
                name=request.POST['name'],
                category=request.POST['category'],
                sku=sku,
                price=float(request.POST['price']),
                cost=float(request.POST['cost']),
                stock_level=int(request.POST['stock_level']),
                reorder_point=int(request.POST['reorder_point'])
            )
            messages.success(request, f"Product '{product.name}' added successfully.")
            # Check if the new product needs a low stock alert
            _create_low_stock_alert(request.user, product)
            # Refresh KPIs immediately for dynamic dashboard
            AnalyticsService.calculate_kpis(request.user)
        except Exception as e:
            print(f"Error adding product: {e}")
            messages.error(request, f"Error adding product: {str(e)}")
    return redirect('inventory:list')


@login_required
def update_stock(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk, user_id=request.user.id)
        try:
            new_stock = int(request.POST['stock_level'])
            Product.objects.filter(pk=pk, user_id=request.user.id).update(stock_level=new_stock)
            product.stock_level = new_stock
            messages.success(request, f"Stock updated for {product.name}.")

            # Auto-resolve or create alerts based on new stock level
            if product.stock_level > product.reorder_point:
                _resolve_alerts_for_product(request.user, product)
            else:
                _create_low_stock_alert(request.user, product)
            
            # Refresh KPIs
            AnalyticsService.calculate_kpis(request.user)

        except Exception as e:
            print(f"Error updating stock: {e}")
            messages.error(request, f"Error updating stock: {str(e)}")
    return redirect('inventory:list')
