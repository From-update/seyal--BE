from django.contrib import admin
from .models import Task, TaskSubmission, Comment, Attachment

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'workspace', 'project', 'assignee', 'status', 'priority', 'due_date', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')

@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'submitted_by', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('target_type', 'target_id', 'user', 'created_at')
    search_fields = ('body',)
