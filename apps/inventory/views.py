from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Product
from django.contrib import messages
from automation.models import Alert
from dashboard.services import AnalyticsService


# Helper functions for alert checking are now handled automatically by signals.py


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
            product.stock_level = new_stock
            product.save(update_fields=['stock_level'])
            messages.success(request, f"Stock updated for {product.name}.")

            # Refresh KPIs
            AnalyticsService.calculate_kpis(request.user)

        except Exception as e:
            print(f"Error updating stock: {e}")
            messages.error(request, f"Error updating stock: {str(e)}")
    return redirect('inventory:list')
