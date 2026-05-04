import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

import requests
from django.contrib.auth.models import User
from inventory.models import Product
from finance.models import Transaction, Expense
from dashboard.models import KPISnapshot
from dashboard.services import AnalyticsService

# Get the CORRECT user
user = User.objects.get(email='ibrahimnasir436@gmail.com')
print(f"User: {user.username} ({user.email})")

# ── Step 1: Clear old data ─────────────────────────────────────
Transaction.objects.filter(user=user).delete()
Expense.objects.filter(user=user).delete()
KPISnapshot.objects.filter(user=user).delete()
Product.objects.filter(user=user).delete()
print("Cleared old data for this user.")

# ── Step 2: Seed products ──────────────────────────────────────
toys = [
    {"name": "Aero X-1 Drone",       "sku": "TOY-DRONE-001",   "price": 35000, "cost": 20000, "stock_level": 15, "reorder_point": 5},
    {"name": "Cyber Mech",            "sku": "TOY-ROBOT-002",   "price": 65000, "cost": 40000, "stock_level": 8,  "reorder_point": 2},
    {"name": "Galactic Explorer Lego","sku": "TOY-LEGO-003",    "price": 25000, "cost": 15000, "stock_level": 40, "reorder_point": 10},
    {"name": "Neon Drift RC",         "sku": "TOY-CAR-004",     "price": 18500, "cost": 10000, "stock_level": 25, "reorder_point": 5},
    {"name": "Hoverboard 3000",       "sku": "TOY-HOVER-005",   "price": 45000, "cost": 25000, "stock_level": 12, "reorder_point": 3},
    {"name": "VR Space Helmet",       "sku": "TOY-VR-006",      "price": 42000, "cost": 25000, "stock_level": 20, "reorder_point": 5},
    {"name": "Plasma Blaster",        "sku": "TOY-BLASTER-007", "price": 8500,  "cost": 4000,  "stock_level": 60, "reorder_point": 15},
    {"name": "Robo-Dog Buddy",        "sku": "TOY-DOG-008",     "price": 32000, "cost": 18000, "stock_level": 18, "reorder_point": 4},
    {"name": "Quantum Puzzle Cube",   "sku": "TOY-CUBE-009",    "price": 4500,  "cost": 2000,  "stock_level": 100,"reorder_point": 20},
    {"name": "Space Rocket",          "sku": "TOY-ROCKET-011",  "price": 22000, "cost": 12000, "stock_level": 30, "reorder_point": 8},
]

for toy in toys:
    Product.objects.create(
        user=user,
        name=toy["name"],
        sku=toy["sku"],
        category="Toys",
        price=toy["price"],
        cost=toy["cost"],
        stock_level=toy["stock_level"],
        reorder_point=toy["reorder_point"]
    )
print(f"Seeded {len(toys)} products for {user.email}")

# ── Step 3: Reset store orders to Pending & sync ──────────────
store_url = "http://localhost:3001/orders"
try:
    r = requests.get(store_url)
    orders = r.json()
    
    # Reset synced orders back to their original status for a fresh demo
    for order in orders:
        if order.get("status") == "Synced":
            order_id = order.get("id")
            requests.patch(f"{store_url}/{order_id}", json={"status": "Pending"})
    
    # Re-fetch
    r = requests.get(store_url)
    orders = r.json()
    pending = [o for o in orders if o.get("status") == "Pending"]
    print(f"\nPending orders to sync: {len(pending)}")
    
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
            order_id = order.get("id")
            requests.patch(f"{store_url}/{order_id}", json={"status": "Synced"})
            synced += 1
            print(f"  Synced: {sku} x{qty} = PKR {total}")
        except Product.DoesNotExist:
            print(f"  SKIP: {sku} not found")
    
    print(f"\nTotal synced: {synced}")
except Exception as e:
    print(f"Store sync error: {e}")

# ── Step 4: Add some sample expenses ──────────────────────────
expenses = [
    {"category": "Rent", "amount": 50000, "description": "Monthly shop rent"},
    {"category": "Utilities", "amount": 12000, "description": "Electricity & Internet"},
    {"category": "Packaging", "amount": 8000, "description": "Boxes & wrapping materials"},
    {"category": "Marketing", "amount": 15000, "description": "Social media ads"},
]
for exp in expenses:
    Expense.objects.create(
        user_id=user.id,
        category=exp["category"],
        amount=exp["amount"],
        description=exp["description"]
    )
print(f"Added {len(expenses)} expenses (total PKR {sum(e['amount'] for e in expenses)})")

# ── Step 5: Calculate KPIs ────────────────────────────────────
print(f"\nTotal transactions: {Transaction.objects.filter(user=user).count()}")
print(f"Total products: {Product.objects.filter(user=user).count()}")
AnalyticsService.calculate_kpis(user)
print("\n✅ ALL DONE! Refresh your dashboard now.")
