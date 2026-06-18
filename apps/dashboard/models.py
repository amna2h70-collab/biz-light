from djongo import models
from django.contrib.auth.models import User

class KPISnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rgr = models.FloatField(verbose_name="Revenue Growth Rate")
    itr = models.FloatField(verbose_name="Inventory Turnover Ratio")
    er = models.FloatField(verbose_name="Expense Ratio")
    scp = models.FloatField(verbose_name="Stock Coverage Period")
    bhs = models.FloatField(verbose_name="Business Health Score")
    total_revenue = models.FloatField(default=0.0, verbose_name="Total Revenue")
    total_expenses = models.FloatField(default=0.0, verbose_name="Total Expenses")
    net_profit = models.FloatField(default=0.0, verbose_name="Net Profit")
    report_type = models.CharField(max_length=20, default='Monthly', verbose_name="Report Period")
    ai_summary = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Snapshot {self.timestamp} - BHS: {self.bhs}"

    @property
    def rgr_percentage(self):
        return (self.rgr or 0) * 100

    @property
    def er_percentage(self):
        return (self.er or 0) * 100

    class Meta:
        ordering = ['-timestamp']

class StoreIntegration(models.Model):
    PLATFORM_CHOICES = [
        ('custom', 'Custom API (WonderToyz / JSON Server)'),
        ('shopify', 'Shopify'),
        ('woocommerce', 'WooCommerce'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store_integration')
    store_name = models.CharField(max_length=255, default='My Store')
    platform_type = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='custom')
    store_url = models.URLField(help_text="e.g. http://localhost:3001/orders")
    api_key = models.CharField(max_length=255, help_text="Your secret API Key")
    created_at = models.DateTimeField(auto_now_add=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.store_name} ({self.get_platform_type_display()})"
