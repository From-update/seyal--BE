from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response

from content.models import Page
from tasks.models import Task
from workspaces.models import WorkspaceMember, Department
from content.serializers import PageSerializer
from tasks.serializers import TaskSerializer
from workspaces.serializers import WorkspaceMemberSerializer

class GlobalSearchView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        workspace_id = request.query_params.get('workspace_id')

        if not query:
            return Response({'pages': [], 'tasks': [], 'members': []})

        pages_qs = Page.objects.filter(is_archived=False, title__icontains=query)
        tasks_qs = Task.objects.filter(title__icontains=query)
        members_qs = WorkspaceMember.objects.filter(status='active', user__name__icontains=query)

        if workspace_id:
            pages_qs = pages_qs.filter(workspace_id=workspace_id)
            tasks_qs = tasks_qs.filter(workspace_id=workspace_id)
            members_qs = members_qs.filter(workspace_id=workspace_id)

        return Response({
            'pages': PageSerializer(pages_qs[:10], many=True).data,
            'tasks': TaskSerializer(tasks_qs[:10], many=True).data,
            'members': WorkspaceMemberSerializer(members_qs[:10], many=True).data
        })

class DepartmentReportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        departments = Department.objects.filter(workspace_id=workspace_id)
        stats = []

        total_tasks = Task.objects.filter(workspace_id=workspace_id).count()
        total_completed = Task.objects.filter(workspace_id=workspace_id, status__in=['completed', 'approved']).count()
        total_overdue = Task.objects.filter(workspace_id=workspace_id, due_date__lt=now).exclude(status__in=['completed', 'approved']).count()

        for dept in departments:
            dept_tasks = Task.objects.filter(department=dept)
            count = dept_tasks.count()
            completed = dept_tasks.filter(status__in=['completed', 'approved']).count()
            overdue = dept_tasks.filter(due_date__lt=now).exclude(status__in=['completed', 'approved']).count()
            in_review = dept_tasks.filter(status='submitted').count()

            stats.append({
                'id': str(dept.id),
                'name': dept.name,
                'manager_name': dept.manager.name if dept.manager else 'Unassigned',
                'total_tasks': count,
                'completed': completed,
                'overdue': overdue,
                'in_review': in_review,
                'completion_rate': round((completed / count * 100), 1) if count > 0 else 0
            })

        return Response({
            'overview': {
                'total_tasks': total_tasks,
                'total_completed': total_completed,
                'total_overdue': total_overdue,
                'overall_completion_rate': round((total_completed / total_tasks * 100), 1) if total_tasks > 0 else 0
            },
            'departments': stats
        })

class MemberReportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        members = WorkspaceMember.objects.filter(workspace_id=workspace_id, status='active').select_related('user')
        stats = []

        for m in members:
            assigned = Task.objects.filter(workspace_id=workspace_id, assignee=m.user)
            total = assigned.count()
            completed = assigned.filter(status__in=['completed', 'approved']).count()
            overdue = assigned.filter(due_date__lt=now).exclude(status__in=['completed', 'approved']).count()

            stats.append({
                'user_id': str(m.user.id),
                'name': m.user.name or m.user.email or m.user.phone,
                'role': m.role,
                'total_tasks': total,
                'completed': completed,
                'overdue': overdue,
                'completion_rate': round((completed / total * 100), 1) if total > 0 else 0
            })

        return Response(stats)

