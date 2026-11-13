from django.urls import path
from .views import (
    WorkspaceListCreateView, WorkspaceDetailView, WorkspaceConvertView,
    WorkspaceMembersView, MemberDetailView,
    DepartmentListCreateView, DepartmentDetailView,
    WorkspaceInviteCreateView, AcceptInviteView
)

urlpatterns = [
    path('workspaces', WorkspaceListCreateView.as_view(), name='workspaces_list_create'),
    path('workspaces/<uuid:pk>', WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('workspaces/<uuid:pk>/convert', WorkspaceConvertView.as_view(), name='workspace_convert'),
    path('workspaces/<uuid:pk>/members', WorkspaceMembersView.as_view(), name='workspace_members'),
    path('members/<uuid:pk>', MemberDetailView.as_view(), name='member_detail'),
    path('workspaces/<uuid:pk>/departments', DepartmentListCreateView.as_view(), name='workspace_departments'),
    path('departments/<uuid:pk>', DepartmentDetailView.as_view(), name='department_detail'),
    path('workspaces/<uuid:pk>/invites', WorkspaceInviteCreateView.as_view(), name='workspace_invites'),
    path('invites/<str:token>/accept', AcceptInviteView.as_view(), name='accept_invite'),
]

