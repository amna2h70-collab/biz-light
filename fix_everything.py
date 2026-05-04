"""
Master fix script: Reset db.json orders, sync for active user, backfill KPIs.
Run with: venv\Scripts\python.exe fix_everything.py
"""
import os, sys, json, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from finance.models import Transaction
from inventory.models import Product
from dashboard.models import KPISnapshot, StoreIntegration
from dashboard.services import AnalyticsService
from dashboard.views import sync_store_data

# ── CONFIG ──
USER_EMAIL = 'ibrahim.urdux@gmail.com'

user = User.objects.get(email=USER_EMAIL)
print(f"[1/6] Target user: {user.email} (id={user.id})")

# ── Step 1: Reset db.json orders to Pending ──
db_path = os.path.join('stores', 'db.json')
with open(db_path, 'r', encoding='utf-8') as f:
    db = json.load(f)

for order in db['orders']:
    order['status'] = 'Pending'

with open(db_path, 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2)

print(f"[2/6] Reset {len(db['orders'])} orders in db.json to 'Pending'")

# ── Step 2: Clear old transactions for this user ──
old_count = Transaction.objects.filter(user=user).count()
Transaction.objects.filter(user=user).delete()
print(f"[3/6] Cleared {old_count} old transactions for user")

# ── Step 3: Ensure StoreIntegration exists ──
si, created = StoreIntegration.objects.get_or_create(
    user=user,
    defaults={
        'store_name': 'WonderToyz',
        'platform_type': 'custom',
        'store_url': 'http://localhost:3001/orders',
        'api_key': 'demo-key',
    }
)
if not si.store_url or 'localhost' not in si.store_url:
    si.store_url = 'http://localhost:3001/orders'
    si.save()
print(f"[3.5/6] StoreIntegration URL: {si.store_url}")

# ── Step 4: Run sync ──
request = RequestFactory().get('/dashboard/sync-store/')
request.user = user
setattr(request, 'session', 'session')
setattr(request, '_messages', FallbackStorage(request))

response = sync_store_data(request)
new_txs = Transaction.objects.filter(user=user).count()
print(f"[4/6] Sync complete (HTTP {response.status_code}). Transactions created: {new_txs}")

if new_txs == 0:
    print("  WARNING: Zero transactions synced! Check json-server is running on port 3001.")
    sys.exit(1)

# ── Step 5: Delete old KPI snapshots and backfill ──
KPISnapshot.objects.filter(user=user).delete()
now = timezone.now()
original_now = timezone.now

for i in range(14, -1, -1):
    d = now - datetime.timedelta(days=i)
    timezone.now = lambda d=d: d  # capture d in closure
    AnalyticsService.calculate_kpis(user, force_new=True, period='daily')

timezone.now = original_now

snap_count = KPISnapshot.objects.filter(user=user).count()
print(f"[5/6] Backfilled {snap_count} KPI snapshots")

# ── Step 6: Verify ──
latest = KPISnapshot.objects.filter(user=user).order_by('-timestamp').first()
if latest:
    print(f"[6/6] Latest snapshot: Revenue={latest.total_revenue}, Profit={latest.net_profit}, BHS={latest.bhs}")
else:
    print("[6/6] WARNING: No snapshots found!")

# Show revenue per day
for s in KPISnapshot.objects.filter(user=user).order_by('timestamp'):
    print(f"  {s.timestamp.strftime('%Y-%m-%d')}: Rev=PKR {s.total_revenue}, Profit=PKR {s.net_profit}, BHS={s.bhs}")

print("")
print("ALL DONE! Refresh your dashboard now.")
