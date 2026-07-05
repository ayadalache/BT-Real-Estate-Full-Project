from rest_framework.permissions import BasePermission


class IsListingRealtorOrAdmin(BasePermission):
    """Only the listing's owning realtor or an Admin may view/manage an inquiry about it."""

    message = "You may only view or manage inquiries for your own listings."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == user.Role.ADMIN:
            return True
        return obj.listing.realtor_id == user.id
