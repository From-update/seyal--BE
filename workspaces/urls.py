from django.urls import path
from .views import (
    SubdivisionsListView,
    WorkspaceListCreateView, WorkspaceDetailView, WorkspaceConvertView,
    WorkspaceMembersView, MemberDetailView,
    DepartmentListCreateView, DepartmentDetailView,
    WorkspaceInviteCreateView, AcceptInviteView,
    SuperadminAnalyticsView, SuperadminOrganisationsView, SuperadminOrganisationDetailView,
    OrganisationOverviewView, OrganisationProjectsView, ProjectDetailView,
    OrganisationUsersView, OrganisationReportsView
)

urlpatterns = [
    # Subdivisions
    path('subdivisions', SubdivisionsListView.as_view(), name='subdivisions_list'),

    # Workspaces
    path('workspaces', WorkspaceListCreateView.as_view(), name='workspaces_list_create'),
    path('workspaces/<uuid:pk>', WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('workspaces/<uuid:pk>/convert', WorkspaceConvertView.as_view(), name='workspace_convert'),
    path('workspaces/<uuid:pk>/members', WorkspaceMembersView.as_view(), name='workspace_members'),
    path('members/<uuid:pk>', MemberDetailView.as_view(), name='member_detail'),
    path('workspaces/<uuid:pk>/departments', DepartmentListCreateView.as_view(), name='workspace_departments'),
    path('departments/<uuid:pk>', DepartmentDetailView.as_view(), name='department_detail'),
    path('workspaces/<uuid:pk>/invites', WorkspaceInviteCreateView.as_view(), name='workspace_invites'),
    path('invites/<str:token>/accept', AcceptInviteView.as_view(), name='accept_invite'),

    # Superadmin (Platform Owner)
    path('superadmin/analytics', SuperadminAnalyticsView.as_view(), name='superadmin_analytics'),
    path('superadmin/organisations', SuperadminOrganisationsView.as_view(), name='superadmin_organisations'),
    path('superadmin/organisations/<uuid:pk>', SuperadminOrganisationDetailView.as_view(), name='superadmin_organisation_detail'),

    # Organisation Subdivision
    path('organisations/<uuid:pk>/overview', OrganisationOverviewView.as_view(), name='organisation_overview'),
    path('organisations/<uuid:pk>/projects', OrganisationProjectsView.as_view(), name='organisation_projects'),
    path('organisations/<uuid:pk>/users', OrganisationUsersView.as_view(), name='organisation_users'),
    path('organisations/<uuid:pk>/reports', OrganisationReportsView.as_view(), name='organisation_reports'),
    path('projects/<uuid:pk>', ProjectDetailView.as_view(), name='project_detail'),
]


