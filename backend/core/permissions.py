"""
Base role-based permission classes.

Roles (see apps.users.models.User.Role): ADMIN, STAFF, USER.
Anonymous requests never satisfy any of these (all require authentication
first), enforcing the Least Privilege Principle by default.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.ADMIN
        )


class IsStaffOrAdmin(BasePermission):
    message = "Only staff or administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (request.user.Role.ADMIN, request.user.Role.STAFF)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allows access if the requesting user owns the
    object (object must expose a `user` or `owner` attribute) or is an admin.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == request.user.Role.ADMIN:
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "owner", None)
        return owner is not None and owner == request.user


class ReadOnlyOrStaffOrAdmin(BasePermission):
    """
    Anyone (subject to view-level auth requirements) may read (GET/HEAD/OPTIONS);
    only staff/admin may write. Useful for public listing endpoints later.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (request.user.Role.ADMIN, request.user.Role.STAFF)
        )
