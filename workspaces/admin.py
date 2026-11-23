from django.contrib import admin
from .models import Workspace, WorkspaceMember, Department

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'plan', 'owner', 'created_at')
    list_filter = ('type', 'plan')
    search_fields = ('name', 'slug')

@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'user', 'role', 'status', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('user__email', 'workspace__name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'head', 'created_at')
    search_fields = ('name', 'workspace__name')
