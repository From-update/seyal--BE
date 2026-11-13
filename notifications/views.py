from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import Notification, ActivityLog
from .serializers import NotificationSerializer, ActivityLogSerializer

class NotificationListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'notifications': NotificationSerializer(notifications, many=True).data,
            'unread_count': unread_count
        })

class NotificationMarkReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        notification = Notification.objects.filter(id=pk, user=request.user).first()
        if not notification:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)

class NotificationReadAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})

class ActivityLogListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, workspace_id):
        activities = ActivityLog.objects.filter(workspace_id=workspace_id).select_related('user').order_by('-created_at')[:100]
        return Response(ActivityLogSerializer(activities, many=True).data)

