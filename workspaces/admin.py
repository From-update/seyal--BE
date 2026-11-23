from django.contrib import admin
from .models import Organisation, Workspace, WorkspaceMember, Department, Project, ProjectMember

@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('is_active', 'subscription_plan')
    search_fields = ('name', 'email', 'phone')

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdivision', 'type', 'plan', 'owner', 'created_at')
    list_filter = ('subdivision', 'type', 'plan')
    search_fields = ('name', 'slug')

@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'role', 'status', 'employee_id', 'designation', 'joined_at')
    list_filter = ('role', 'status')
    search_fields = ('user__email', 'workspace__name', 'employee_id')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'manager', 'created_at')
    search_fields = ('name', 'workspace__name')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_id_code', 'organisation', 'workspace', 'project_manager', 'onboarding_status', 'lifecycle_status', 'priority')
    list_filter = ('onboarding_status', 'lifecycle_status', 'priority')
    search_fields = ('name', 'project_id_code')

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'joined_at')
    search_fields = ('project__name', 'user__email')
