from celery import shared_task
from .services import AnalyticsService
from ai_layer.services import AIService
from automation.models import Alert

@shared_task
def update_business_analytics():
    # Calculate KPIs
    snapshot = AnalyticsService.calculate_kpis()
    
    # Get unresolved alerts
    alerts = Alert.objects.filter(is_resolved__in=[False])
    
    # Generate AI Summary
    ai_service = AIService()
    summary = ai_service.generate_business_summary(snapshot, alerts)
    
    # Update snapshot with summary
    snapshot.ai_summary = summary
    snapshot.save()
    
    return f"Analytics updated for {snapshot.timestamp}"
