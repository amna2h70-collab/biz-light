from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory.models import Product
from finance.models import Transaction, Expense
from dashboard.models import KPISnapshot
from automation.models import Alert
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Seed database with demo data for a user'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")
        
        # Get or create demo user
        user, created = User.objects.get_or_create(username='demo')
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write(f"Created demo user: demo / demo1234")

        # 1. Clear existing data for this user
        Product.objects.filter(user=user).delete()
        Transaction.objects.filter(user=user).delete()
        Expense.objects.filter(user=user).delete()
        KPISnapshot.objects.filter(user=user).delete()
        Alert.objects.filter(user=user).delete()

        # 2. Create Products
        products_data = [
            {'name': 'Artisanal Coffee Beans', 'category': 'Beverages', 'sku': 'COF-001', 'price': 25.00, 'cost': 12.00, 'stock': 45, 'reorder': 10},
            {'name': 'Organic Honey Jar', 'category': 'Food', 'sku': 'HON-002', 'price': 15.00, 'cost': 7.50, 'stock': 8, 'reorder': 10},
            {'name': 'Handmade Ceramic Mug', 'category': 'Home', 'sku': 'MUG-003', 'price': 18.00, 'cost': 5.00, 'stock': 20, 'reorder': 5},
            {'name': 'Lavender Essential Oil', 'category': 'Wellness', 'sku': 'OIL-004', 'price': 12.00, 'cost': 4.00, 'stock': 30, 'reorder': 10},
        ]
        
        products = []
        for data in products_data:
            p = Product.objects.create(
                user=user,
                name=data['name'], category=data['category'], sku=data['sku'],
                price=data['price'], cost=data['cost'],
                stock_level=data['stock'], reorder_point=data['reorder']
            )
            products.append(p)

        # 3. Create Transactions (Last 60 days)
        now = timezone.now()
        for i in range(60):
            date = now - timedelta(days=i)
            # Random sales
            for _ in range(random.randint(1, 5)):
                p = random.choice(products)
                qty = random.randint(1, 3)
                Transaction.objects.create(
                    user=user,
                    product=p, type='SALE', quantity=qty,
                    total_amount=p.price * qty, timestamp=date
                )

        # 4. Create Expenses
        expense_cats = ['Rent', 'Utilities', 'Supplies', 'Marketing']
        for i in range(2):
            for cat in expense_cats:
                Expense.objects.create(
                    user=user,
                    category=cat, amount=random.randint(50, 200),
                    description=f"Monthly {cat}", date=(now - timedelta(days=i*30)).date()
                )

        # 5. Create Alerts
        Alert.objects.create(
            user=user,
            type='LOW_STOCK', message="Stock low for Organic Honey Jar (8 left). Reorder recommended.",
            severity='MEDIUM', timestamp=now
        )

        # 6. Create initial KPI snapshots for the chart
        for i in range(7):
            KPISnapshot.objects.create(
                user=user,
                rgr=random.uniform(0.05, 0.2),
                itr=random.uniform(2.0, 4.0),
                er=random.uniform(0.1, 0.3),
                scp=random.uniform(15, 45),
                bhs=random.uniform(70, 85),
                timestamp=now - timedelta(days=(7-i)*2),
                ai_summary="Historical snapshot for trend analysis."
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded database for user: {user.username}"))
