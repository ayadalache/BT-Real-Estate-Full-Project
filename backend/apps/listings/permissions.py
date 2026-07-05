from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsRealtorOwnerOrAdmin(BasePermission):
    """
    Staff (realtors) may create listings and manage only their own; Admins
    may manage any listing. Enforces Least Privilege: a realtor should never
    be able to edit a colleague's listing.
    """

    message = "You may only modify listings you own, unless you are an administrator."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (request.user.Role.ADMIN, request.user.Role.STAFF)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == request.user.Role.ADMIN:
            return True
        return obj.realtor_id == request.user.id


class CanViewListing(BasePermission):
    """
    Public users may only view ACTIVE listings. The owning realtor and
    Admins may view a listing regardless of status (e.g. to review a
    PENDING or INACTIVE draft).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user and user.is_authenticated:
            if user.role == user.Role.ADMIN or obj.realtor_id == user.id:
                return True
        return obj.status == obj.Status.ACTIVE
