from django.urls import path
from .views import (
    NotificationListView, NotificationMarkReadView,
    NotificationReadAllView, ActivityLogListView
)

urlpatterns = [
    path('notifications', NotificationListView.as_view(), name='notifications_list'),
    path('notifications/<uuid:pk>/read', NotificationMarkReadView.as_view(), name='notification_read'),
    path('notifications/read-all', NotificationReadAllView.as_view(), name='notifications_read_all'),
    path('workspaces/<uuid:workspace_id>/activities', ActivityLogListView.as_view(), name='workspace_activities'),
]

