from rest_framework import serializers
from .models import Notification, ActivityLog
from accounts.serializers import UserSerializer

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'workspace', 'type', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'workspace', 'user', 'action', 'entity_type', 'entity_id', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']

