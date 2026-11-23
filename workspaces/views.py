import datetime
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.db import transaction
from rest_framework import views, status, permissions
from rest_framework.response import Response

from .models import (
    Organisation, Workspace, WorkspaceMember, Department,
    DepartmentMember, Project, ProjectMember, WorkspaceInvite
)
from .serializers import (
    OrganisationSerializer, WorkspaceSerializer, WorkspaceMemberSerializer,
    DepartmentSerializer, ProjectSerializer, ProjectMemberSerializer,
    WorkspaceInviteSerializer
)
from accounts.models import User, AuthIdentity, LoginAudit
from accounts.serializers import UserSerializer
from tasks.models import Task
from billing.models import PaymentRecord, Subscription

# --------------------------------------------------------------------------- #
# SUBDIVISIONS HUB VIEW                                                       #
# --------------------------------------------------------------------------- #
class SubdivisionsListView(views.APIView):
    """
    Returns the four master SEYAL subdivisions with user-specific workspace counts
    and access readiness.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        accessible_workspaces = Workspace.objects.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__status='active')
        ).distinct()

        # Group counts by subdivision
        subdivisions_data = [
            {
                'id': 'organisation',
                'name': 'Organisation',
                'title': 'Organisation Workspace',
                'description': 'Manage organisations, employees, managers, departments, projects and business operations.',
                'icon': 'Building2',
                'color': '#08745B',
                'workspace_count': accessible_workspaces.filter(subdivision='organisation').count(),
                'is_available': True,
            },
            {
                'id': 'personal',
                'name': 'Personal',
                'title': 'Personal Workspace',
                'description': 'Manage personal tasks, habits, goals, schedules, notes and productivity.',
                'icon': 'User',
                'color': '#2563EB',
                'workspace_count': accessible_workspaces.filter(subdivision='personal').count(),
                'is_available': True,
            },
            {
                'id': 'freelancer',
                'name': 'Freelancer',
                'title': 'Freelancer Workspace',
                'description': 'Manage freelance clients, projects, deliverables, deadlines and work activities.',
                'icon': 'Briefcase',
                'color': '#7C3AED',
                'workspace_count': accessible_workspaces.filter(subdivision='freelancer').count(),
                'is_available': True,
            },
            {
                'id': 'customize',
                'name': 'Customize',
                'title': 'Custom Workspace',
                'description': 'Create a configurable workspace according to individual or business requirements.',
                'icon': 'Sliders',
                'color': '#D97706',
                'workspace_count': accessible_workspaces.filter(subdivision='customize').count(),
                'is_available': True,
            },
        ]

        return Response({
            'user': UserSerializer(user).data,
            'subdivisions': subdivisions_data,
        })

# --------------------------------------------------------------------------- #
# WORKSPACES CRUD                                                             #
# --------------------------------------------------------------------------- #
class WorkspaceListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        subdivision = request.query_params.get('subdivision')
        qs = Workspace.objects.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__status='active')
        ).distinct().order_by('-created_at')

        if subdivision:
            qs = qs.filter(subdivision=subdivision)

        serializer = WorkspaceSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        ws_type = request.data.get('type', 'team')
        subdivision = request.data.get('subdivision', 'organisation' if ws_type in ['team', 'organization'] else 'personal')

        if ws_type == 'personal' and subdivision == 'personal':
            if Workspace.objects.filter(owner=user, type='personal').exists():
                return Response({'error': 'You already have a personal workspace'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', f"{user.name or 'My'} Workspace")
        organisation_id = request.data.get('organisation_id')
        org = Organisation.objects.filter(id=organisation_id).first() if organisation_id else None

        workspace = Workspace.objects.create(
            name=name,
            type=ws_type,
            subdivision=subdivision,
            organisation=org,
            plan=request.data.get('plan', 'free'),
            owner=user,
            settings=request.data.get('settings', {"icon": "💼", "theme": "default"})
        )

        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role='org_superadmin' if org and org.owner_id == user.id else 'owner',
            status='active'
        )

        return Response(WorkspaceSerializer(workspace, context={'request': request}).data, status=status.HTTP_201_CREATED)

class WorkspaceDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self, pk, user):
        return Workspace.objects.filter(
            Q(id=pk) & (Q(owner=user) | Q(memberships__user=user, memberships__status='active') | Q(owner__is_superuser=True))
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

        is_owner = workspace.owner_id == request.user.id or request.user.is_superuser
        is_admin = workspace.memberships.filter(user=request.user, role__in=['owner', 'admin', 'org_superadmin', 'org_admin']).exists()
        if not (is_owner or is_admin):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkspaceSerializer(workspace, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        workspace = self.get_workspace(pk, request.user)
        if not workspace or (workspace.owner_id != request.user.id and not request.user.is_superuser):
            return Response({'error': 'Only owner or superadmin can delete workspace'}, status=status.HTTP_403_FORBIDDEN)
        workspace.delete()
        return Response({'message': 'Workspace deleted'})

class WorkspaceConvertView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = Workspace.objects.filter(id=pk, owner=request.user).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        if workspace.type != 'personal':
            return Response({'error': 'Workspace is already a team/organization workspace'}, status=status.HTTP_400_BAD_REQUEST)

        workspace.type = 'team'
        workspace.subdivision = 'organisation'
        workspace.save(update_fields=['type', 'subdivision'])
        return Response(WorkspaceSerializer(workspace, context={'request': request}).data)

class WorkspaceMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        members = WorkspaceMember.objects.filter(workspace_id=pk, status='active').select_related('user', 'department', 'reporting_manager')
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
            defaults={
                'role': role,
                'status': 'active',
                'employee_id': request.data.get('employee_id', ''),
                'designation': request.data.get('designation', ''),
                'department_id': request.data.get('department_id'),
                'reporting_manager_id': request.data.get('reporting_manager_id'),
            }
        )
        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

class MemberDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        member = WorkspaceMember.objects.filter(id=pk).first()
        if not member:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

        is_owner = member.workspace.owner_id == request.user.id or request.user.is_superuser
        is_admin = member.workspace.memberships.filter(user=request.user, role__in=['owner', 'admin', 'org_superadmin', 'org_admin']).exists()
        if not (is_owner or is_admin):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        for field in ['role', 'status', 'employee_id', 'designation', 'department_id', 'reporting_manager_id', 'joining_date']:
            if field in request.data:
                setattr(member, field, request.data[field])
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

# --------------------------------------------------------------------------- #
# DEPARTMENTS CRUD                                                            #
# --------------------------------------------------------------------------- #
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
            description=serializer.validated_data.get('description', ''),
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

# --------------------------------------------------------------------------- #
# SEYAL PRODUCT SUPER ADMIN APIS (GLOBAL PLATFORM OWNER)                      #
# --------------------------------------------------------------------------- #
class SuperadminAnalyticsView(views.APIView):
    """
    Platform-wide analytics for the Seyal Product Owner / Super Admin.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Superadmin privileges required'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        thirty_days_ago = now - datetime.timedelta(days=30)
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Organisations
        total_orgs = Organisation.objects.count()
        active_orgs = Organisation.objects.filter(is_active=True).count()
        inactive_orgs = total_orgs - active_orgs
        new_orgs_month = Organisation.objects.filter(created_at__gte=first_day_this_month).count()

        # Users & Admins
        total_users = User.objects.count()
        total_org_admins = WorkspaceMember.objects.filter(role__in=['org_superadmin', 'org_admin']).values('user').distinct().count()

        # Revenue metrics
        total_rev = PaymentRecord.objects.filter(status='captured').aggregate(val=Sum('amount'))['val'] or 0
        monthly_rev = PaymentRecord.objects.filter(status='captured', created_at__gte=first_day_this_month).aggregate(val=Sum('amount'))['val'] or 0
        annual_rev = total_rev # In dev/pilot, equivalent
        pending_payments = PaymentRecord.objects.filter(status='pending').count()
        failed_payments = PaymentRecord.objects.filter(status='failed').count()
        active_subscriptions = Subscription.objects.filter(status='active').count()

        # Product & Activity
        dau = LoginAudit.objects.filter(created_at__gte=now - datetime.timedelta(days=1), success=True).values('user').distinct().count() or 1
        mau = LoginAudit.objects.filter(created_at__gte=thirty_days_ago, success=True).values('user').distinct().count() or total_users
        total_workspaces = Workspace.objects.count()

        # Subscriptions distribution
        plan_dist = list(Organisation.objects.values('subscription_plan').annotate(count=Count('id')))

        return Response({
            'organisations': {
                'total': total_orgs,
                'active': active_orgs,
                'inactive': inactive_orgs,
                'new_this_month': new_orgs_month,
                'total_admins': total_org_admins,
                'total_users': total_users,
            },
            'revenue': {
                'total_inr': total_rev,
                'monthly_inr': monthly_rev,
                'annual_inr': annual_rev,
                'pending_payments': pending_payments,
                'failed_payments': failed_payments,
                'active_subscriptions': active_subscriptions,
            },
            'product': {
                'total_users': total_users,
                'dau': dau,
                'mau': mau,
                'total_workspaces': total_workspaces,
                'plan_distribution': plan_dist,
            }
        })

class SuperadminOrganisationsView(views.APIView):
    """
    List all organisations or provision a new organisation with owner account atomically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Superadmin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        orgs = Organisation.objects.all().select_related('owner').order_by('-created_at')
        return Response(OrganisationSerializer(orgs, many=True).data)

    def post(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Superadmin privileges required'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        name = data.get('name', '').strip()
        owner_email = data.get('owner_email', '').strip().lower()
        owner_name = data.get('owner_name', '').strip()
        owner_phone = data.get('owner_phone', '').strip()
        subscription_plan = data.get('subscription_plan', 'free')

        if not name or not owner_email:
            return Response({'error': 'Organisation name and Owner email are required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 1. Create or retrieve owner user
            owner = User.objects.filter(email=owner_email).first()
            if not owner:
                owner = User.objects.create_user(
                    email=owner_email,
                    phone=owner_phone or None,
                    name=owner_name or owner_email.split('@')[0].capitalize(),
                    email_verified=True,
                    usage_mode='team'
                )
                owner.set_password(data.get('owner_password') or 'Welcome@123')
                owner.save()
                AuthIdentity.objects.create(
                    user=owner,
                    provider='password',
                    provider_user_id=owner_email,
                    provider_email=owner_email,
                    is_verified=True
                )

            # 2. Create Organisation
            org = Organisation.objects.create(
                name=name,
                logo_url=data.get('logo_url', ''),
                email=data.get('email', owner_email),
                phone=data.get('phone', owner_phone),
                address=data.get('address', ''),
                industry=data.get('industry', ''),
                registration_number=data.get('registration_number', ''),
                owner=owner,
                subscription_plan=subscription_plan,
                is_active=True
            )

            # 3. Create Root Workspace for Organisation
            ws = Workspace.objects.create(
                name=f"{name} Operations",
                type='organization',
                subdivision='organisation',
                organisation=org,
                plan=subscription_plan,
                owner=owner,
                settings={"icon": "🏢", "theme": "emerald"}
            )

            # 4. Enroll Owner as Organisation Super Admin
            WorkspaceMember.objects.create(
                workspace=ws,
                user=owner,
                role='org_superadmin',
                designation='Company Owner & CEO',
                status='active'
            )

            owner.default_workspace_id = str(ws.id)
            owner.save(update_fields=['default_workspace_id'])

        return Response(OrganisationSerializer(org).data, status=status.HTTP_201_CREATED)

class SuperadminOrganisationDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({'error': 'Superadmin privileges required'}, status=status.HTTP_403_FORBIDDEN)
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrganisationSerializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

# --------------------------------------------------------------------------- #
# ORGANISATION SUBDIVISION: OWNER & ADMIN APIS                                #
# --------------------------------------------------------------------------- #
class OrganisationOverviewView(views.APIView):
    """
    Returns real-time aggregated KPIs for Company Owner & Admin.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        # Permission check: superadmin, org owner, or active workspace member
        is_owner = org.owner_id == request.user.id or request.user.is_superuser
        is_member = WorkspaceMember.objects.filter(workspace__organisation=org, user=request.user, status='active').exists()
        if not (is_owner or is_member):
            return Response({'error': 'Access denied to this organisation'}, status=status.HTTP_403_FORBIDDEN)

        # 1. Employee & Department Metrics
        members_qs = WorkspaceMember.objects.filter(workspace__organisation=org, status='active')
        total_employees = members_qs.values('user').distinct().count()
        total_departments = Department.objects.filter(workspace__organisation=org).count()
        total_managers = members_qs.filter(role__in=[
            'lead_manager', 'department_manager', 'project_manager', 'hr_manager', 'finance_manager'
        ]).values('user').distinct().count()

        # 2. Project Metrics
        projects_qs = Project.objects.filter(organisation=org)
        total_projects = projects_qs.count()
        onboarded_projects = projects_qs.filter(onboarding_status='onboarded').count()
        unboarded_projects = projects_qs.filter(onboarding_status='unboarded').count()
        ongoing_projects = projects_qs.filter(lifecycle_status='ongoing').count()
        completed_projects = projects_qs.filter(lifecycle_status='completed').count()

        # 3. Task Metrics
        tasks_qs = Task.objects.filter(workspace__organisation=org)
        total_tasks = tasks_qs.count()
        completed_tasks = tasks_qs.filter(status='completed').count()
        pending_tasks = tasks_qs.exclude(status='completed').count()
        now = timezone.now()
        overdue_tasks = tasks_qs.filter(status__in=['todo', 'in_progress', 'rejected'], due_date__lt=now).count()
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

        # 4. Department Performance Breakdown
        departments = Department.objects.filter(workspace__organisation=org).annotate(
            dept_tasks=Count('projects__tasks', distinct=True)
        )
        dept_breakdown = []
        for d in departments:
            d_tasks = Task.objects.filter(Q(department=d) | Q(project__department=d))
            d_tot = d_tasks.count()
            d_done = d_tasks.filter(status='completed').count()
            dept_breakdown.append({
                'id': str(d.id),
                'name': d.name,
                'total_tasks': d_tot,
                'completed_tasks': d_done,
                'rate': round((d_done / d_tot * 100), 1) if d_tot > 0 else 0.0
            })

        # 5. Recent Projects Snapshot
        recent_projects = ProjectSerializer(projects_qs.order_by('-created_at')[:5], many=True).data

        return Response({
            'kpis': {
                'total_employees': total_employees,
                'total_departments': total_departments,
                'total_managers': total_managers,
                'total_projects': total_projects,
                'onboarded_projects': onboarded_projects,
                'unboarded_projects': unboarded_projects,
                'ongoing_projects': ongoing_projects,
                'completed_projects': completed_projects,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'overdue_tasks': overdue_tasks,
                'task_completion_rate': completion_rate,
            },
            'department_performance': dept_breakdown,
            'recent_projects': recent_projects,
            'organisation': OrganisationSerializer(org).data
        })

class OrganisationProjectsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = Project.objects.filter(organisation=org).select_related('project_manager', 'department', 'workspace')
        onboarding = request.query_params.get('onboarding')
        lifecycle = request.query_params.get('lifecycle')
        if onboarding:
            qs = qs.filter(onboarding_status=onboarding)
        if lifecycle:
            qs = qs.filter(lifecycle_status=lifecycle)

        return Response(ProjectSerializer(qs.order_by('-created_at'), many=True).data)

    def post(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get or choose default workspace for organisation
        ws = org.workspaces.first()
        if not ws:
            ws = Workspace.objects.create(
                name=f"{org.name} Workspace",
                type='organization',
                subdivision='organisation',
                organisation=org,
                owner=org.owner
            )

        data = request.data
        pm_id = data.get('project_manager_id')
        dept_id = data.get('department_id')

        project = Project.objects.create(
            organisation=org,
            workspace=ws,
            department_id=dept_id or None,
            project_id_code=data.get('project_id_code', f"PRJ-{Project.objects.filter(organisation=org).count() + 1:03d}"),
            name=data.get('name'),
            description=data.get('description', ''),
            project_manager_id=pm_id or None,
            onboarding_status=data.get('onboarding_status', 'unboarded'),
            lifecycle_status=data.get('lifecycle_status', 'ongoing'),
            priority=data.get('priority', 'medium'),
            start_date=data.get('start_date') or None,
            expected_completion_date=data.get('expected_completion_date') or None,
            created_by=request.user
        )

        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

class ProjectDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project = Project.objects.filter(id=pk).first()
        if not project:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProjectSerializer(project).data)

    def patch(self, request, pk):
        project = Project.objects.filter(id=pk).first()
        if not project:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProjectSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if 'project_manager_id' in request.data:
            project.project_manager_id = request.data.get('project_manager_id') or None
        serializer.save()
        return Response(ProjectSerializer(project).data)

class OrganisationUsersView(views.APIView):
    """
    Enterprise user management: list, invite, and create roles.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        members = WorkspaceMember.objects.filter(
            workspace__organisation=org
        ).select_related('user', 'department', 'reporting_manager').order_by('-joined_at')

        return Response(WorkspaceMemberSerializer(members, many=True).data)

    def post(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        role = data.get('role', 'staff')
        phone = data.get('phone', '').strip()
        employee_id = data.get('employee_id', '').strip()
        designation = data.get('designation', '').strip()
        dept_id = data.get('department_id')
        manager_id = data.get('reporting_manager_id')

        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        ws = org.workspaces.first()
        if not ws:
            ws = Workspace.objects.create(name=f"{org.name} Workspace", organisation=org, owner=org.owner)

        with transaction.atomic():
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    email=email,
                    name=name or email.split('@')[0].capitalize(),
                    phone=phone or None,
                    email_verified=True,
                    usage_mode='team'
                )
                user.set_password(data.get('password') or 'SeyalUser@2026')
                user.save()
                AuthIdentity.objects.create(
                    user=user,
                    provider='password',
                    provider_user_id=email,
                    provider_email=email,
                    is_verified=True
                )

            member, _ = WorkspaceMember.objects.update_or_create(
                workspace=ws,
                user=user,
                defaults={
                    'role': role,
                    'status': 'active',
                    'employee_id': employee_id,
                    'designation': designation,
                    'department_id': dept_id or None,
                    'reporting_manager_id': manager_id or None,
                    'joining_date': data.get('joining_date') or timezone.now().date(),
                }
            )

        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

class OrganisationReportsView(views.APIView):
    """
    Dynamic reporting engine across departments, projects, managers, employees.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        org = Organisation.objects.filter(id=pk).first()
        if not org:
            return Response({'error': 'Organisation not found'}, status=status.HTTP_404_NOT_FOUND)

        tasks = Task.objects.filter(workspace__organisation=org)

        # Department performance
        dept_reports = []
        for d in Department.objects.filter(workspace__organisation=org):
            d_tasks = tasks.filter(Q(department=d) | Q(project__department=d))
            tot = d_tasks.count()
            done = d_tasks.filter(status='completed').count()
            dept_reports.append({
                'department_name': d.name,
                'manager_name': d.manager.name if d.manager else 'Unassigned',
                'total_tasks': tot,
                'completed_tasks': done,
                'pending_tasks': tot - done,
                'rate': round((done / tot * 100), 1) if tot > 0 else 0.0,
            })

        # Project performance
        proj_reports = []
        for p in Project.objects.filter(organisation=org):
            p_tasks = tasks.filter(project=p)
            tot = p_tasks.count()
            done = p_tasks.filter(status='completed').count()
            proj_reports.append({
                'project_name': p.name,
                'project_id_code': p.project_id_code,
                'manager_name': p.project_manager.name if p.project_manager else 'Unassigned',
                'onboarding_status': p.onboarding_status,
                'lifecycle_status': p.lifecycle_status,
                'total_tasks': tot,
                'completed_tasks': done,
                'pending_tasks': tot - done,
                'progress_percentage': round((done / tot * 100)) if tot > 0 else 0,
            })

        # Employee performance
        emp_reports = []
        for m in WorkspaceMember.objects.filter(workspace__organisation=org, status='active').select_related('user', 'department'):
            u_tasks = tasks.filter(assignee=m.user)
            tot = u_tasks.count()
            done = u_tasks.filter(status='completed').count()
            emp_reports.append({
                'name': m.user.name or m.user.email,
                'email': m.user.email,
                'role': m.role,
                'department': m.department.name if m.department else 'General',
                'total_assigned': tot,
                'completed': done,
                'completion_rate': round((done / tot * 100), 1) if tot > 0 else 0.0,
            })

        return Response({
            'department_reports': dept_reports,
            'project_reports': proj_reports,
            'employee_reports': emp_reports,
        })
