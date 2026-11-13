from django.urls import path
from .views import PlanListView, WorkspaceSubscriptionView, CreateOrderView, ConfirmPaymentView

urlpatterns = [
    path('plans', PlanListView.as_view(), name='plans_list'),
    path('workspaces/<uuid:workspace_id>/subscription', WorkspaceSubscriptionView.as_view(), name='workspace_subscription'),
    path('workspaces/<uuid:workspace_id>/create-order', CreateOrderView.as_view(), name='create_order'),
    path('workspaces/<uuid:workspace_id>/confirm-payment', ConfirmPaymentView.as_view(), name='confirm_payment'),
]

