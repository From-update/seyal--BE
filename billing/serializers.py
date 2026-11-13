from rest_framework import serializers
from .models import Plan, Subscription, PaymentRecord

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'slug', 'price_inr_monthly', 'price_inr_yearly', 'max_members', 'max_storage_mb', 'features', 'is_active']

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'workspace', 'plan', 'status', 'billing_cycle', 'current_period_end', 'razorpay_subscription_id', 'created_at']

