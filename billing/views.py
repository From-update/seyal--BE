import uuid
import datetime
from django.utils import timezone
from rest_framework import views, status, permissions
from rest_framework.response import Response

from .models import Plan, Subscription, PaymentRecord
from .serializers import PlanSerializer, SubscriptionSerializer
from workspaces.models import Workspace

DEFAULT_PLANS = [
    {
        "name": "Free",
        "slug": "free",
        "price_inr_monthly": 0.00,
        "price_inr_yearly": 0.00,
        "max_members": 5,
        "max_storage_mb": 500,
        "features": [
            "Unlimited personal pages & notes",
            "Up to 5 team members",
            "Kanban Board & Table views",
            "Standard task hierarchy",
            "500MB storage"
        ]
    },
    {
        "name": "Pro",
        "slug": "pro",
        "price_inr_monthly": 299.00,
        "price_inr_yearly": 2990.00,
        "max_members": 25,
        "max_storage_mb": 10240,
        "features": [
            "Up to 25 members",
            "Recurring tasks & reminders",
            "Advanced department analytics",
            "10GB cloud storage",
            "Custom page templates",
            "Priority email support"
        ]
    },
    {
        "name": "Business",
        "slug": "business",
        "price_inr_monthly": 799.00,
        "price_inr_yearly": 7990.00,
        "max_members": 150,
        "max_storage_mb": 51200,
        "features": [
            "Unlimited departments & hierarchy",
            "Full approval workflows (Owner → Manager → Staff)",
            "Up to 150 team members",
            "50GB cloud storage",
            "Audit logs & role-based permissions",
            "Dedicated onboarding manager"
        ]
    },
    {
        "name": "Enterprise",
        "slug": "enterprise",
        "price_inr_monthly": 1999.00,
        "price_inr_yearly": 19990.00,
        "max_members": 1000,
        "max_storage_mb": 524288,
        "features": [
            "Dedicated database option",
            "Custom domain & branding",
            "SAML / SSO login",
            "500GB+ storage",
            "99.9% uptime SLA",
            "24/7 phone & WhatsApp support"
        ]
    }
]

def ensure_plans():
    for p in DEFAULT_PLANS:
        Plan.objects.get_or_create(slug=p['slug'], defaults=p)

class PlanListView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        ensure_plans()
        plans = Plan.objects.filter(is_active=True).order_by('price_inr_monthly')
        return Response(PlanSerializer(plans, many=True).data)

class WorkspaceSubscriptionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, workspace_id):
        sub = Subscription.objects.filter(workspace_id=workspace_id, status='active').first()
        if not sub:
            # Return free tier as default
            free_plan = Plan.objects.filter(slug='free').first()
            if not free_plan:
                ensure_plans()
                free_plan = Plan.objects.filter(slug='free').first()
            return Response({
                'workspace_id': str(workspace_id),
                'plan': PlanSerializer(free_plan).data,
                'status': 'active',
                'billing_cycle': 'monthly',
                'current_period_end': None
            })
        return Response(SubscriptionSerializer(sub).data)

class CreateOrderView(views.APIView):
    """
    Razorpay Order Creation simulation & integration (Section 13).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, workspace_id):
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        plan_slug = request.data.get('plan_slug')
        billing_cycle = request.data.get('billing_cycle', 'monthly') # 'monthly' or 'yearly'
        plan = Plan.objects.filter(slug=plan_slug).first()
        if not plan:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

        amount = plan.price_inr_yearly if billing_cycle == 'yearly' else plan.price_inr_monthly

        if amount == 0:
            # Instant free plan upgrade/downgrade
            workspace.plan = plan.slug
            workspace.save(update_fields=['plan'])
            Subscription.objects.update_or_create(
                workspace=workspace,
                defaults={
                    'plan': plan,
                    'status': 'active',
                    'billing_cycle': billing_cycle,
                    'current_period_end': timezone.now() + datetime.timedelta(days=365)
                }
            )
            return Response({
                'message': 'Switched to Free plan',
                'plan': PlanSerializer(plan).data,
                'status': 'success'
            })

        order_id = f"order_{str(uuid.uuid4())[:12]}"
        payment = PaymentRecord.objects.create(
            workspace=workspace,
            amount=amount,
            currency='INR',
            razorpay_order_id=order_id,
            status='created'
        )

        return Response({
            'order_id': order_id,
            'amount_in_paise': int(amount * 100),
            'currency': 'INR',
            'plan': PlanSerializer(plan).data,
            'billing_cycle': billing_cycle
        })

class ConfirmPaymentView(views.APIView):
    """
    Verifies payment success and activates workspace subscription.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, workspace_id):
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        order_id = request.data.get('order_id')
        payment_id = request.data.get('payment_id', f"pay_{str(uuid.uuid4())[:10]}")
        plan_slug = request.data.get('plan_slug')
        billing_cycle = request.data.get('billing_cycle', 'monthly')

        plan = Plan.objects.filter(slug=plan_slug).first()
        if not plan:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

        payment = PaymentRecord.objects.filter(workspace=workspace, razorpay_order_id=order_id).first()
        if payment:
            payment.razorpay_payment_id = payment_id
            payment.status = 'captured'
            payment.save()

        # Update workspace plan
        workspace.plan = plan.slug
        workspace.save(update_fields=['plan'])

        days = 365 if billing_cycle == 'yearly' else 30
        subscription, _ = Subscription.objects.update_or_create(
            workspace=workspace,
            defaults={
                'plan': plan,
                'status': 'active',
                'billing_cycle': billing_cycle,
                'current_period_end': timezone.now() + datetime.timedelta(days=days),
                'razorpay_subscription_id': payment_id
            }
        )

        return Response({
            'message': f"Successfully subscribed to {plan.name} plan!",
            'subscription': SubscriptionSerializer(subscription).data,
            'workspace_plan': workspace.plan
        })

