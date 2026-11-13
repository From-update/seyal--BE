import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import Workspace, WorkspaceMember, Department, DepartmentMember, WorkspaceInvite
from .serializers import WorkspaceSerializer, WorkspaceMemberSerializer, DepartmentSerializer, WorkspaceInviteSerializer
from accounts.models import User

class WorkspaceListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Workspaces user owns or is a member of
        workspaces = Workspace.objects.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__status='active')
        ).distinct().order_by('-created_at')
        serializer = WorkspaceSerializer(workspaces, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        ws_type = request.data.get('type', 'team')

        if ws_type == 'personal':
            if Workspace.objects.filter(owner=user, type='personal').exists():
                return Response({'error': 'You already have a personal workspace'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', f"{user.name or 'My'} Workspace")
        workspace = Workspace.objects.create(
            name=name,
            type=ws_type,
            plan=request.data.get('plan', 'free'),
            owner=user,
            settings=request.data.get('settings', {"icon": "💼", "theme": "default"})
        )

        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role='owner',
            status='active'
        )

        return Response(WorkspaceSerializer(workspace, context={'request': request}).data, status=status.HTTP_201_CREATED)

# Workspaces imports Q
from django.db.models import Q

class WorkspaceDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self, pk, user):
        return Workspace.objects.filter(
            Q(id=pk) & (Q(owner=user) | Q(memberships__user=user, memberships__status='active'))
        ).distinct().first()

    def get(self, request, pk):
        workspace = self.get_workspace(pk, request.user)
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(WorkspaceSerializer(workspace, context={'request': request}).data)

    def patch(self, request, pk):
        workspace = self.get_workspace(pk, request.user)
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check permission: only owner or admin can edit settings
        is_owner = workspace.owner_id == request.user.id
        is_admin = workspace.memberships.filter(user=request.user, role__in=['owner', 'admin']).exists()
        if not (is_owner or is_admin):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkspaceSerializer(workspace, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        workspace = self.get_workspace(pk, request.user)
        if not workspace or workspace.owner_id != request.user.id:
            return Response({'error': 'Only owner can delete workspace'}, status=status.HTTP_403_FORBIDDEN)
        workspace.delete()
        return Response({'message': 'Workspace deleted'})

class WorkspaceConvertView(views.APIView):
    """
    Converts a Personal workspace into a Team workspace (Section 4A).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = Workspace.objects.filter(id=pk, owner=request.user).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        if workspace.type != 'personal':
            return Response({'error': 'Workspace is already a team/organization workspace'}, status=status.HTTP_400_BAD_REQUEST)

        workspace.type = 'team'
        workspace.save(update_fields=['type'])
        return Response(WorkspaceSerializer(workspace, context={'request': request}).data)

class WorkspaceMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        members = WorkspaceMember.objects.filter(workspace_id=pk, status='active').select_related('user')
        return Response(WorkspaceMemberSerializer(members, many=True).data)

    def post(self, request, pk):
        workspace = Workspace.objects.filter(id=pk).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        role = request.data.get('role', 'member')
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        member, _ = WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            user=user,
            defaults={'role': role, 'status': 'active'}
        )
        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

class MemberDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        member = WorkspaceMember.objects.filter(id=pk).first()
        if not member:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

        # Ensure user is owner/admin of workspace
        is_owner = member.workspace.owner_id == request.user.id
        is_admin = member.workspace.memberships.filter(user=request.user, role__in=['owner', 'admin']).exists()
        if not (is_owner or is_admin):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role')
        if role:
            member.role = role
        status_val = request.data.get('status')
        if status_val:
            member.status = status_val
        member.save()
        return Response(WorkspaceMemberSerializer(member).data)

    def delete(self, request, pk):
        member = WorkspaceMember.objects.filter(id=pk).first()
        if not member:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        if member.user_id == member.workspace.owner_id:
            return Response({'error': 'Cannot remove the workspace owner'}, status=status.HTTP_400_BAD_REQUEST)
        member.delete()
        return Response({'message': 'Member removed'})

class DepartmentListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        departments = Department.objects.filter(workspace_id=pk).select_related('manager')
        return Response(DepartmentSerializer(departments, many=True).data)

    def post(self, request, pk):
        workspace = Workspace.objects.filter(id=pk).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        manager = None
        manager_id = serializer.validated_data.get('manager_id')
        if manager_id:
            manager = User.objects.filter(id=manager_id).first()

        department = Department.objects.create(
            workspace=workspace,
            name=serializer.validated_data['name'],
            parent=serializer.validated_data.get('parent'),
            manager=manager
        )
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)

class DepartmentDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        department = Department.objects.filter(id=pk).first()
        if not department:
            return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepartmentSerializer(department, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if 'manager_id' in request.data:
            manager_id = request.data.get('manager_id')
            department.manager = User.objects.filter(id=manager_id).first() if manager_id else None
        serializer.save()
        return Response(DepartmentSerializer(department).data)

    def delete(self, request, pk):
        department = Department.objects.filter(id=pk).first()
        if not department:
            return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)
        department.delete()
        return Response({'message': 'Department deleted'})

class WorkspaceInviteCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = Workspace.objects.filter(id=pk).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        email_or_phone = request.data.get('email_or_phone', '').strip()
        role = request.data.get('role', 'member')
        if not email_or_phone:
            return Response({'error': 'Email or phone required'}, status=status.HTTP_400_BAD_REQUEST)

        invite = WorkspaceInvite.objects.create(
            workspace=workspace,
            email_or_phone=email_or_phone,
            role=role,
            expires_at=timezone.now() + datetime.timedelta(days=7),
            created_by=request.user
        )
        return Response(WorkspaceInviteSerializer(invite).data, status=status.HTTP_201_CREATED)

class AcceptInviteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invite = WorkspaceInvite.objects.filter(token=token).first()
        if not invite or not invite.is_valid():
            return Response({'error': 'Invalid or expired invite token'}, status=status.HTTP_400_BAD_REQUEST)

        member, _ = WorkspaceMember.objects.get_or_create(
            workspace=invite.workspace,
            user=request.user,
            defaults={'role': invite.role, 'status': 'active'}
        )
        invite.accepted_at = timezone.now()
        invite.save(update_fields=['accepted_at'])

        return Response({
            'message': 'Invite accepted successfully',
            'workspace': WorkspaceSerializer(invite.workspace, context={'request': request}).data
        })

