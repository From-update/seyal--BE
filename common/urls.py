from django.urls import path
from .views import GlobalSearchView, DepartmentReportView, MemberReportView
from .integrations_views import (
    GoogleDriveView,
    GmailView,
    GmailCreateTaskView,
    ClaudeAiView,
    BirthdayRemindersView,
    BirthdayDeleteView,
    IntegrationSettingsView,
    IntegrationTestConnectionView,
)

urlpatterns = [
    path('search', GlobalSearchView.as_view(), name='global_search'),
    path('reports/department', DepartmentReportView.as_view(), name='department_report'),
    path('reports/members', MemberReportView.as_view(), name='member_report'),
    # Integrations: Google Drive & Gmail
    path('integrations/google/drive', GoogleDriveView.as_view(), name='google_drive'),
    path('integrations/google/gmail', GmailView.as_view(), name='gmail_list'),
    path('integrations/google/gmail/create-task', GmailCreateTaskView.as_view(), name='gmail_create_task'),
    # AI Assistant: Anthropic Claude
    path('ai/claude/generate', ClaudeAiView.as_view(), name='claude_generate'),
    # Birthday & Occasion Reminders
    path('reminders/birthdays', BirthdayRemindersView.as_view(), name='birthday_reminders'),
    path('reminders/birthdays/<str:pk>', BirthdayDeleteView.as_view(), name='birthday_delete'),
    # API Keys & Integration Settings
    path('integrations/settings', IntegrationSettingsView.as_view(), name='integration_settings'),
    path('integrations/test', IntegrationTestConnectionView.as_view(), name='integration_test'),
]
