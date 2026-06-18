from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Transaction, Expense
from inventory.models import Product
from automation.models import Alert
from django.contrib import messages
from django.db.models import Sum
from dashboard.services import AnalyticsService
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json


@login_required
def transaction_list(request):
    period = request.GET.get('period', 'monthly')
    from django.utils import timezone
    import datetime
    
    now = timezone.now()
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = None

    transactions = Transaction.objects.filter(user_id=request.user.id).order_by('-timestamp')[:50]
    expenses = Expense.objects.filter(user_id=request.user.id).order_by('-date')[:50]
    products = Product.objects.filter(user_id=request.user.id)
    
    # Filter for totals
    if start_date:
        filtered_transactions = Transaction.objects.filter(user_id=request.user.id, type='SALE', timestamp__gte=start_date)
        filtered_expenses = Expense.objects.filter(user_id=request.user.id, date__gte=start_date.date())
    else:
        filtered_transactions = Transaction.objects.filter(user_id=request.user.id, type='SALE')
        filtered_expenses = Expense.objects.filter(user_id=request.user.id)
        
    total_sales = sum(t.total_amount for t in filtered_transactions)
    total_expenses = sum(e.amount for e in filtered_expenses)
    
    # Calculate COGS
    total_cogs = 0
    for t in filtered_transactions:
        try:
            total_cogs += (t.quantity * t.product.cost)
        except Exception:
            pass
    
    context = {
        'transactions': transactions,
        'expenses': expenses,
        'products': products,
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'net_profit': total_sales - total_cogs - total_expenses,
        'current_period': period,
        'page_title': 'Financial Records'
    }
    return render(request, 'finance/list.html', context)


@login_required
def log_sale(request):
    if request.method == 'POST':
        product_id = request.POST['product_id']
        quantity = int(request.POST['quantity'])
        product = Product.objects.get(id=product_id, user_id=request.user.id)
        
        if product.stock_level < quantity:
            messages.error(request, f"Insufficient stock for {product.name}.")
        else:
            total = product.price * quantity
            Transaction.objects.create(
                user_id=request.user.id,
                product=product,
                type='SALE',
                quantity=quantity,
                total_amount=total
            )
            product.stock_level -= quantity
            product.save(update_fields=['stock_level'])
            messages.success(request, f"Sale logged: {quantity}x {product.name}.")
            
            # Refresh KPIs
            AnalyticsService.calculate_kpis(request.user)
            
        return redirect('finance:transactions')


@login_required
def log_expense(request):
    if request.method == 'POST':
        Expense.objects.create(
            user_id=request.user.id,
            category=request.POST['category'],
            amount=float(request.POST['amount']),
            description=request.POST['description'],
            date=request.POST['date']
        )
        messages.success(request, "Expense logged successfully.")
        # Refresh KPIs
        AnalyticsService.calculate_kpis(request.user)
        return redirect('finance:transactions')


@csrf_exempt
def webhook_sale(request):
    """
    Simulated webhook endpoint for external e-commerce integration.
    Expects JSON: {"api_key": "...", "sku": "...", "quantity": ...}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        # In a real app, we'd validate the api_key and map it to a user.
        # For this project, we'll assume a 'demo' user or use the first user for simulation.
        from django.contrib.auth.models import User
        user = User.objects.first() # Default to first user for demo purposes
        
        sku = data.get('sku')
        quantity = int(data.get('quantity', 1))
        
        product = Product.objects.get(sku=sku, user_id=user.id)
        
        if product.stock_level < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
            
        total = product.price * quantity
        Transaction.objects.create(
            user_id=user.id,
            product=product,
            type='SALE',
            quantity=quantity,
            total_amount=total
        )
        product.stock_level -= quantity
        product.save(update_fields=['stock_level'])
        
        # Refresh KPIs
        AnalyticsService.calculate_kpis(user)
        
        return JsonResponse({'status': 'success', 'message': f'Logged sale for {product.name}'})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
