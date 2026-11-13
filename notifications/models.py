import uuid
from django.db import models
from django.conf import settings
from workspaces.models import Workspace

class Notification(models.Model):
    TYPE_CHOICES = [
        ('assignment', 'Task Assignment'),
        ('submission', 'Task Submitted'),
        ('approval', 'Task Approved'),
        ('rejection', 'Task Changes Requested'),
        ('mention', 'Mentioned'),
        ('comment', 'Comment Added'),
        ('reminder', 'Task Due Reminder'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='assignment')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.title}"

class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=32)
    entity_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

