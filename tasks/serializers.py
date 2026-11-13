from rest_framework import serializers
from .models import Task, TaskSubmission, Comment, Attachment
from accounts.serializers import UserSerializer
from workspaces.serializers import DepartmentSerializer, WorkspaceSerializer

class TaskSubmissionSerializer(serializers.ModelSerializer):
    submitted_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = TaskSubmission
        fields = [
            'id', 'task', 'submitted_by', 'note', 'attachments',
            'status', 'reviewed_by', 'reviewed_at', 'review_note', 'created_at'
        ]
        read_only_fields = ['id', 'submitted_by', 'reviewed_by', 'reviewed_at', 'created_at', 'task']

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'target_type', 'target_id', 'user', 'body', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    assigned_by = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.UUIDField(write_only=True)
    latest_submission = serializers.SerializerMethodField()
    subtasks_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'workspace', 'workspace_id', 'department', 'department_id',
            'title', 'description', 'status', 'priority',
            'assignee', 'assignee_id', 'assigned_by', 'due_date',
            'parent_task', 'recurring_rule', 'labels',
            'latest_submission', 'subtasks_count', 'comments_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'workspace', 'department', 'assigned_by', 'created_at', 'updated_at']

    def get_latest_submission(self, obj):
        submission = obj.submissions.order_by('-created_at').first()
        return TaskSubmissionSerializer(submission).data if submission else None

    def get_subtasks_count(self, obj):
        return obj.subtasks.count()

    def get_comments_count(self, obj):
        return Comment.objects.filter(target_type='task', target_id=obj.id).count()

