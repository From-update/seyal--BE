from rest_framework import permissions

class HasWorkspaceAccess(permissions.BasePermission):
    """
    Ensures the user is an active member or owner of the workspace passed in the request or object.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', None)
        if not workspace and hasattr(obj, 'workspace_id'):
            from workspaces.models import Workspace
            workspace = Workspace.objects.filter(id=obj.workspace_id).first()
        elif hasattr(obj, 'type') and hasattr(obj, 'owner'): # If obj is Workspace itself
            workspace = obj

        if not workspace:
            return True

        if workspace.owner_id == request.user.id:
            return True

        return workspace.memberships.filter(user=request.user, status='active').exists()

class IsWorkspaceOwnerOrAdmin(permissions.BasePermission):
    """
    Ensures user is Owner or Admin in the workspace.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', None) or (obj if hasattr(obj, 'owner') else None)
        if not workspace:
            return True
        if workspace.owner_id == request.user.id:
            return True
        return workspace.memberships.filter(
            user=request.user,
            role__in=['owner', 'admin'],
            status='active'
        ).exists()

