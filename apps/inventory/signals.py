from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product
from automation.models import Alert

@receiver(post_save, sender=Product)
def product_stock_alert_handler(sender, instance, **kwargs):
    """
    Signal handler to automatically create or resolve alerts when a Product's stock changes.
    This hooks into all stock changes (manual updates, sales logs, WooCommerce/Shopify sync, webhooks).
    """
    # 1. Check if stock is low
    if instance.stock_level <= instance.reorder_point:
        # Check if there's already an unresolved low stock alert for this product
        # Query utilizing the ForeignKey relationship
        already_exists = Alert.objects.filter(
            user_id=instance.user.id,
            product=instance,
            type='LOW_STOCK',
            is_resolved__in=[False]
        ).exists()
        
        # Fallback query for legacy alerts that might match by name
        if not already_exists:
            existing = list(Alert.objects.filter(
                user_id=instance.user.id,
                type='LOW_STOCK',
                is_resolved__in=[False]
            ))
            already_exists = any(instance.name in a.message for a in existing)
            
        if not already_exists:
            severity = 'CRITICAL' if instance.stock_level == 0 else 'HIGH' if instance.stock_level <= instance.reorder_point // 2 else 'MEDIUM'
            Alert.objects.create(
                user_id=instance.user.id,
                product=instance,
                type='LOW_STOCK',
                message=f"Stock low for {instance.name} ({instance.stock_level} left). Reorder recommended.",
                severity=severity
            )
    else:
        # 2. Stock is healthy, so resolve any existing alerts for this product
        # Update using foreign key
        Alert.objects.filter(
            user_id=instance.user.id,
            product=instance,
            type='LOW_STOCK',
            is_resolved__in=[False]
        ).update(is_resolved=True)
        
        # Fallback for legacy alerts matching by name
        legacy_alerts = Alert.objects.filter(
            user_id=instance.user.id,
            type='LOW_STOCK',
            is_resolved__in=[False]
        )
        for alert in legacy_alerts:
            if instance.name in alert.message:
                alert.is_resolved = True
                alert.save()
