from rest_framework import serializers
from .models import Workspace, WorkspaceMember, Department, DepartmentMember, WorkspaceInvite
from accounts.serializers import UserSerializer

class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'slug', 'type', 'plan',
            'owner', 'settings', 'member_count', 'my_role',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'owner', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(status='active').count()

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        if obj.owner_id == request.user.id:
            return 'owner'
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'workspace', 'user', 'user_id', 'role', 'status', 'joined_at']
        read_only_fields = ['id', 'joined_at', 'workspace']

class DepartmentSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    manager_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'workspace', 'name', 'parent', 'manager', 'manager_id', 'member_count', 'created_at']
        read_only_fields = ['id', 'workspace', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()

class WorkspaceInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvite
        fields = ['id', 'workspace', 'email_or_phone', 'role', 'token', 'expires_at', 'accepted_at', 'created_at']
        read_only_fields = ['id', 'token', 'accepted_at', 'created_at', 'workspace']

