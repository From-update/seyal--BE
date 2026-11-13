import uuid
from django.db import models
from workspaces.models import Workspace

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64, unique=True)
    price_inr_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_inr_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_members = models.IntegerField(default=5)
    max_storage_mb = models.IntegerField(default=500)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (₹{self.price_inr_monthly}/mo)"

class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, default='active')
    billing_cycle = models.CharField(max_length=20, default='monthly') # monthly, yearly
    current_period_end = models.DateTimeField(null=True, blank=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.workspace.name} - {self.plan.name} ({self.status})"

class PaymentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    razorpay_order_id = models.CharField(max_length=100, blank=True, default='')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=30, default='created')
    created_at = models.DateTimeField(auto_now_add=True)

