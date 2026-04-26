from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Alert
from django.contrib import messages

@login_required
def alert_list(request):
    alerts = Alert.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'automation/alerts.html', {'alerts': alerts, 'page_title': 'Alert Center'})

@login_required
def resolve_alert(request, pk):
    alert = get_object_or_404(Alert, pk=pk, user=request.user)
    Alert.objects.filter(pk=pk, user=request.user).update(is_resolved=True)
    messages.success(request, "Alert marked as resolved.")
    return redirect('automation:alerts')
