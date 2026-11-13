from django.urls import path
from .views import (
    TaskListCreateView, TaskDetailView,
    TaskSubmitView, TaskReviewView,
    MyTasksView, TaskCommentsView
)

urlpatterns = [
    path('tasks', TaskListCreateView.as_view(), name='tasks_list_create'),
    path('tasks/<uuid:pk>', TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<uuid:pk>/submit', TaskSubmitView.as_view(), name='task_submit'),
    path('tasks/<uuid:pk>/review', TaskReviewView.as_view(), name='task_review'),
    path('tasks/<uuid:pk>/comments', TaskCommentsView.as_view(), name='task_comments'),
    path('me/tasks', MyTasksView.as_view(), name='my_tasks'),
]

