from django.db import models
from django.contrib.auth.models import User

class BusinessProfile(models.Model):
    BUSINESS_TYPES = [
        ('RETAIL', 'Retail'),
        ('SERVICE', 'Service'),
        ('MANUFACTURING', 'Manufacturing'),
        ('HOME_BASED', 'Home Based'),
        ('OTHER', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_profile')
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name
