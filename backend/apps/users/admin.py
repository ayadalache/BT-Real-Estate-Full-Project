from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_email_verified", "is_active", "created_at")
    list_filter = ("role", "is_email_verified", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("public_id", "created_at", "updated_at", "failed_login_attempts", "locked_until")
    ordering = ("-created_at",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Platform Role", {"fields": ("role", "phone_number", "is_email_verified")}),
        ("Public Profile", {"fields": ("bio", "profile_photo")}),
        ("Security", {"fields": ("failed_login_attempts", "locked_until")}),
        ("Metadata", {"fields": ("public_id", "created_at", "updated_at")}),
    )
