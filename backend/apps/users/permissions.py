from rest_framework.permissions import BasePermission


class IsSelf(BasePermission):
    """Object-level permission restricting access to the user's own record."""

    message = "You may only access your own account."

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj == request.user)
