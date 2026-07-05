from django.contrib import admin

from apps.inquiries.models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "listing", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email", "message", "listing__title")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("listing", "user")
