import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

import requests
from django.contrib.auth.models import User
from inventory.models import Product
from finance.models import Transaction
from dashboard.services import AnalyticsService

user = User.objects.get(email='ibrahimnasir436@gmail.com')
print(f"User: {user.username} ({user.email})")

store_url = "http://localhost:3001/orders"

# Reset synced orders back to Pending
r = requests.get(store_url)
orders = r.json()
for order in orders:
    if order.get("status") == "Synced":
        oid = order.get("id")
        requests.patch(f"{store_url}/{oid}", json={"status": "Pending"})
        print(f"  Reset order {oid} to Pending")

# Re-fetch
r = requests.get(store_url)
orders = r.json()
pending = [o for o in orders if o.get("status") == "Pending"]
print(f"\nPending orders: {len(pending)}")

synced = 0
for order in pending:
    sku = order.get("sku")
    qty = order.get("quantity", 1)
    try:
        product = Product.objects.get(sku=sku, user=user)
        total = product.price * qty
        Transaction.objects.create(
            user_id=user.id,
            product=product,
            type="SALE",
            quantity=qty,
            total_amount=total
        )
        product.stock_level -= qty
        product.save()
        oid = order.get("id")
        requests.patch(f"{store_url}/{oid}", json={"status": "Synced"})
        synced += 1
        print(f"  Synced: {sku} x{qty} = PKR {total}")
    except Product.DoesNotExist:
        print(f"  SKIP: {sku} not found")

print(f"\nTotal synced: {synced}")
print(f"Total transactions: {Transaction.objects.filter(user=user).count()}")
print(f"Total products: {Product.objects.filter(user=user).count()}")

AnalyticsService.calculate_kpis(user)
print("KPIs recalculated! Refresh dashboard now.")
