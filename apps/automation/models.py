from djongo import models
from django.contrib.auth.models import User

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    SEVERITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    type = models.CharField(max_length=50)  # e.g., 'LOW_STOCK', 'EXPENSE_SPIKE'
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.severity} - {self.type}"

class ThresholdConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=50) # Remove unique=True for multi-tenancy
    value = models.FloatField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.key}: {self.value}"
