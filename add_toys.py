import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

from django.contrib.auth.models import User
from inventory.models import Product
from finance.models import Transaction, Expense
from dashboard.models import KPISnapshot

def seed_toys():
    user = User.objects.first()
    if not user:
        print("No user found.")
        return

    # Clear old data to reset currency scaling issues
    Transaction.objects.all().delete()
    Expense.objects.all().delete()
    KPISnapshot.objects.all().delete()
    
    toys = [
        {"name": "Aero X-1 Drone", "sku": "TOY-DRONE-001", "price": 35000.0, "cost": 20000.0, "stock_level": 15, "reorder_point": 5},
        {"name": "Cyber Mech", "sku": "TOY-ROBOT-002", "price": 65000.0, "cost": 40000.0, "stock_level": 8, "reorder_point": 2},
        {"name": "Galactic Explorer Lego", "sku": "TOY-LEGO-003", "price": 25000.0, "cost": 15000.0, "stock_level": 40, "reorder_point": 10},
        {"name": "Neon Drift RC", "sku": "TOY-CAR-004", "price": 18500.0, "cost": 10000.0, "stock_level": 25, "reorder_point": 5},
        {"name": "Hoverboard 3000", "sku": "TOY-HOVER-005", "price": 45000.0, "cost": 25000.0, "stock_level": 12, "reorder_point": 3},
        {"name": "VR Space Helmet", "sku": "TOY-VR-006", "price": 42000.0, "cost": 25000.0, "stock_level": 20, "reorder_point": 5},
        {"name": "Plasma Blaster", "sku": "TOY-BLASTER-007", "price": 8500.0, "cost": 4000.0, "stock_level": 60, "reorder_point": 15},
        {"name": "Robo-Dog Buddy", "sku": "TOY-DOG-008", "price": 32000.0, "cost": 18000.0, "stock_level": 18, "reorder_point": 4},
        {"name": "Quantum Puzzle Cube", "sku": "TOY-CUBE-009", "price": 4500.0, "cost": 2000.0, "stock_level": 100, "reorder_point": 20},
        {"name": "Space Rocket", "sku": "TOY-ROCKET-011", "price": 22000.0, "cost": 12000.0, "stock_level": 30, "reorder_point": 8},
    ]

    for toy in toys:
        Product.objects.update_or_create(
            sku=toy['sku'],
            user=user,
            defaults={
                'name': toy['name'],
                'category': 'Toys',
                'price': toy['price'],
                'cost': toy['cost'],
                'stock_level': toy['stock_level'],
                'reorder_point': toy['reorder_point']
            }
        )
    print("Toys seeded successfully with PKR prices!")

if __name__ == '__main__':
    seed_toys()
