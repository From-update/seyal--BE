from rest_framework import serializers
from .models import Organisation, Workspace, WorkspaceMember, Department, DepartmentMember, Project, ProjectMember, WorkspaceInvite
from accounts.serializers import UserSerializer

class OrganisationSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    workspace_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'slug', 'logo_url', 'email', 'phone',
            'address', 'industry', 'registration_number', 'owner',
            'subscription_plan', 'is_active', 'workspace_count',
            'member_count', 'project_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'owner', 'created_at', 'updated_at']

    def get_workspace_count(self, obj):
        return obj.workspaces.count()

    def get_member_count(self, obj):
        return WorkspaceMember.objects.filter(workspace__organisation=obj, status='active').values('user').distinct().count()

    def get_project_count(self, obj):
        return obj.projects.count()

class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'type', 'subdivision', 'plan',
            'owner', 'organisation', 'organisation_name', 'settings',
            'member_count', 'my_role', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'owner', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(status='active').count()

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        if obj.owner_id == request.user.id:
            # Check if there is a specific enterprise role assigned
            member = obj.memberships.filter(user=request.user).first()
            return member.role if member else 'owner'
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=False)
    department_name = serializers.CharField(source='department.name', read_only=True)
    reporting_manager_name = serializers.CharField(source='reporting_manager.name', read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = [
            'id', 'workspace', 'user', 'user_id', 'role', 'status',
            'employee_id', 'designation', 'department', 'department_name',
            'reporting_manager', 'reporting_manager_name', 'joining_date', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at', 'workspace']

class DepartmentSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    manager_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    member_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'workspace', 'name', 'description', 'parent',
            'manager', 'manager_id', 'member_count', 'project_count', 'created_at'
        ]
        read_only_fields = ['id', 'workspace', 'created_at']

    def get_member_count(self, obj):
        return obj.assigned_workspace_members.count()

    def get_project_count(self, obj):
        return obj.projects.count()

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'project', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']

class ProjectSerializer(serializers.ModelSerializer):
    project_manager = UserSerializer(read_only=True)
    project_manager_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    pending_tasks = serializers.SerializerMethodField()
    overdue_tasks = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'organisation', 'workspace', 'department', 'department_name',
            'project_id_code', 'name', 'description', 'project_manager', 'project_manager_id',
            'onboarding_status', 'lifecycle_status', 'priority', 'start_date', 'expected_completion_date',
            'members', 'total_tasks', 'completed_tasks', 'pending_tasks', 'overdue_tasks',
            'progress_percentage', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_total_tasks(self, obj):
        return obj.tasks.count()

    def get_completed_tasks(self, obj):
        return obj.tasks.filter(status='completed').count()

    def get_pending_tasks(self, obj):
        return obj.tasks.exclude(status='completed').count()

    def get_overdue_tasks(self, obj):
        from django.utils import timezone
        return obj.tasks.filter(status__in=['todo', 'in_progress', 'rejected'], due_date__lt=timezone.now()).count()

    def get_progress_percentage(self, obj):
        total = obj.tasks.count()
        if total == 0:
            return 0
        completed = obj.tasks.filter(status='completed').count()
        return round((completed / total) * 100)

class WorkspaceInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvite
        fields = ['id', 'workspace', 'email_or_phone', 'role', 'token', 'expires_at', 'accepted_at', 'created_at']
        read_only_fields = ['id', 'token', 'accepted_at', 'created_at', 'workspace']
