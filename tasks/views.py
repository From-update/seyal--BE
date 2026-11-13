from django.utils import timezone
from django.db.models import Q
from rest_framework import views, status, permissions
from rest_framework.response import Response

from .models import Task, TaskSubmission, Comment, Attachment
from .serializers import TaskSerializer, TaskSubmissionSerializer, CommentSerializer
from accounts.models import User
from workspaces.models import Workspace, Department
from notifications.models import Notification, ActivityLog

class TaskListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        if not workspace_id:
            return Response({'error': 'workspace_id query param is required'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Task.objects.filter(workspace_id=workspace_id).select_related('assignee', 'assigned_by', 'department', 'workspace')

        department_id = request.query_params.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        assignee_id = request.query_params.get('assignee_id')
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)

        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        return Response(TaskSerializer(queryset.order_by('-created_at'), many=True).data)

    def post(self, request):
        workspace_id = request.data.get('workspace_id')
        workspace = Workspace.objects.filter(id=workspace_id).first()
        if not workspace:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)

        assignee_id = request.data.get('assignee_id')
        assignee = User.objects.filter(id=assignee_id).first() if assignee_id else None

        department_id = request.data.get('department_id')
        department = Department.objects.filter(id=department_id, workspace=workspace).first() if department_id else None

        task = Task.objects.create(
            workspace=workspace,
            department=department,
            title=request.data.get('title', 'New Task'),
            description=request.data.get('description', ''),
            status=request.data.get('status', 'todo'),
            priority=request.data.get('priority', 'medium'),
            assignee=assignee,
            assigned_by=request.user,
            due_date=request.data.get('due_date'),
            recurring_rule=request.data.get('recurring_rule', ''),
            labels=request.data.get('labels', [])
        )

        if assignee and assignee != request.user:
            Notification.objects.create(
                user=assignee,
                workspace=workspace,
                type='assignment',
                title='New Task Assigned',
                message=f"{request.user.name or 'A teammate'} assigned you: {task.title}",
                link=f"/tasks?taskId={task.id}"
            )

        ActivityLog.objects.create(
            workspace=workspace,
            user=request.user,
            action='created_task',
            entity_type='task',
            entity_id=task.id,
            metadata={'title': task.title}
        )

        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

class TaskDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        task = Task.objects.filter(id=pk).select_related('assignee', 'assigned_by', 'department', 'workspace').first()
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TaskSerializer(task).data)

    def patch(self, request, pk):
        task = Task.objects.filter(id=pk).first()
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        if 'assignee_id' in request.data:
            assignee_id = request.data.get('assignee_id')
            task.assignee = User.objects.filter(id=assignee_id).first() if assignee_id else None

        if 'department_id' in request.data:
            dept_id = request.data.get('department_id')
            task.department = Department.objects.filter(id=dept_id).first() if dept_id else None

        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TaskSerializer(task).data)

    def delete(self, request, pk):
        task = Task.objects.filter(id=pk).first()
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        task.delete()
        return Response({'message': 'Task deleted'})

class TaskSubmitView(views.APIView):
    """
    Hierarchy flow: Staff submits completed task with notes and attachments (Section 6).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = Task.objects.filter(id=pk).first()
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        note = request.data.get('note', '')
        attachments = request.data.get('attachments', [])

        submission = TaskSubmission.objects.create(
            task=task,
            submitted_by=request.user,
            note=note,
            attachments=attachments,
            status='pending'
        )

        task.status = 'submitted'
        task.save(update_fields=['status'])

        # Notify assigned_by or Department Manager
        reviewer = None
        if task.department and task.department.manager:
            reviewer = task.department.manager
        elif task.assigned_by:
            reviewer = task.assigned_by
        elif task.workspace.owner:
            reviewer = task.workspace.owner

        if reviewer and reviewer != request.user:
            Notification.objects.create(
                user=reviewer,
                workspace=task.workspace,
                type='submission',
                title='Task Submitted for Review',
                message=f"{request.user.name or 'Staff'} submitted: '{task.title}' for your review.",
                link=f"/tasks?taskId={task.id}"
            )

        ActivityLog.objects.create(
            workspace=task.workspace,
            user=request.user,
            action='submitted_task',
            entity_type='task',
            entity_id=task.id,
            metadata={'note': note[:100]}
        )

        return Response({
            'message': 'Task submitted for review',
            'submission': TaskSubmissionSerializer(submission).data,
            'task': TaskSerializer(task).data
        })

class TaskReviewView(views.APIView):
    """
    Hierarchy flow: Manager reviews submitted task, approves or rejects with reason (Section 6).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = Task.objects.filter(id=pk).first()
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        decision = request.data.get('decision') # 'approve' or 'reject'
        review_note = request.data.get('review_note', '')

        submission = task.submissions.filter(status='pending').order_by('-created_at').first()
        if not submission:
            submission = TaskSubmission.objects.create(
                task=task,
                submitted_by=task.assignee or request.user,
                status='pending'
            )

        if decision == 'approve':
            submission.status = 'approved'
            task.status = 'completed'
            notif_type = 'approval'
            title = 'Task Approved 🎉'
            msg = f"Your work on '{task.title}' has been approved."
        else:
            submission.status = 'rejected'
            task.status = 'rejected'
            notif_type = 'rejection'
            title = 'Changes Requested on Task'
            msg = f"Feedback on '{task.title}': {review_note or 'Please review and resubmit.'}"

        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.review_note = review_note
        submission.save()
        task.save(update_fields=['status'])

        # Notify assignee
        if task.assignee and task.assignee != request.user:
            Notification.objects.create(
                user=task.assignee,
                workspace=task.workspace,
                type=notif_type,
                title=title,
                message=msg,
                link=f"/tasks?taskId={task.id}"
            )

        ActivityLog.objects.create(
            workspace=task.workspace,
            user=request.user,
            action=f"reviewed_task_{decision}",
            entity_type='task',
            entity_id=task.id,
            metadata={'decision': decision, 'feedback': review_note[:100]}
        )

        return Response({
            'message': f"Task {decision}d successfully",
            'task': TaskSerializer(task).data,
            'submission': TaskSubmissionSerializer(submission).data
        })

class MyTasksView(views.APIView):
    """
    Aggregated My Tasks across all workspaces (Section 4A & 10).
    Categorizes tasks into today, upcoming, overdue, and completed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        user_tasks = Task.objects.filter(
            assignee=request.user
        ).select_related('workspace', 'department')

        overdue = user_tasks.filter(
            due_date__lt=today_start
        ).exclude(status__in=['completed', 'approved']).order_by('due_date')

        today = user_tasks.filter(
            due_date__range=(today_start, today_end)
        ).exclude(status__in=['completed', 'approved']).order_by('priority')

        upcoming = user_tasks.filter(
            due_date__gt=today_end
        ).exclude(status__in=['completed', 'approved']).order_by('due_date')

        no_date = user_tasks.filter(
            due_date__isnull=True
        ).exclude(status__in=['completed', 'approved']).order_by('-created_at')

        completed = user_tasks.filter(
            status__in=['completed', 'approved']
        ).order_by('-updated_at')[:20]

        return Response({
            'overdue': TaskSerializer(overdue, many=True).data,
            'today': TaskSerializer(today, many=True).data,
            'upcoming': TaskSerializer(upcoming, many=True).data,
            'no_date': TaskSerializer(no_date, many=True).data,
            'completed': TaskSerializer(completed, many=True).data,
            'total_pending': overdue.count() + today.count() + upcoming.count() + no_date.count()
        })

class TaskCommentsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        comments = Comment.objects.filter(target_type='task', target_id=pk).select_related('user')
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, pk):
        body = request.data.get('body', '').strip()
        if not body:
            return Response({'error': 'Comment body is required'}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(
            target_type='task',
            target_id=pk,
            user=request.user,
            body=body
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

