from django.contrib import admin

from apps.listings.models import Amenity, Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "city", "state", "price", "status", "listing_type", "realtor", "listing_date")
    list_filter = ("status", "listing_type", "state")
    search_fields = ("title", "address_line", "city", "description")
    autocomplete_fields = ("realtor",)
    filter_horizontal = ("amenities",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [ListingImageInline]


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
