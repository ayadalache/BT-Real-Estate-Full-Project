from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser

from apps.listings import services
from apps.listings.filters import ListingFilter
from apps.listings.models import Listing, ListingImage
from apps.listings.permissions import CanViewListing, IsRealtorOwnerOrAdmin
from apps.listings.serializers import (
    ListingDetailSerializer,
    ListingImageSerializer,
    ListingImageUploadSerializer,
    ListingListSerializer,
    ListingWriteSerializer,
)
from core.responses import success_response


class ListingViewSet(viewsets.ModelViewSet):
    """
    /api/v1/listings/            GET (list, public+filterable), POST (Admin/Staff)
    /api/v1/listings/{id}/       GET (public detail), PUT/PATCH/DELETE (owner/Admin)

    Business logic (amenity resolution, realtor assignment rules) lives in
    services.py; this view stays a thin orchestration layer.
    """

    lookup_field = "public_id"
    permission_classes = [CanViewListing, IsRealtorOwnerOrAdmin]
    filterset_class = ListingFilter
    search_fields = ["title", "description", "city", "amenities__name"]
    ordering_fields = ["price", "listing_date", "square_feet", "created_at"]

    def get_queryset(self):
        queryset = (
            Listing.objects.select_related("realtor")
            .prefetch_related("images", "amenities")
        )
        user = self.request.user

        if not (user and user.is_authenticated):
            return queryset.filter(status=Listing.Status.ACTIVE)
        if user.role == user.Role.ADMIN:
            return queryset
        if user.role == user.Role.STAFF:
            from django.db.models import Q
            return queryset.filter(Q(status=Listing.Status.ACTIVE) | Q(realtor=user))
        return queryset.filter(status=Listing.Status.ACTIVE)

    def get_serializer_class(self):
        if self.action == "list":
            return ListingListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ListingWriteSerializer
        return ListingDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()  # enforces CanViewListing.has_object_permission
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        amenity_names = validated.pop("amenity_names", None)
        realtor = validated.pop("realtor", None) or request.user

        listing = services.create_listing(realtor=realtor, amenity_names=amenity_names, **validated)
        output = ListingDetailSerializer(listing, context=self.get_serializer_context())
        return success_response(output.data, message="Listing created successfully.", status_code=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()  # enforces IsRealtorOwnerOrAdmin.has_object_permission
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        amenity_names = validated.pop("amenity_names", None)

        if "realtor" in validated and request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Only administrators may reassign a listing's realtor.")

        listing = services.update_listing(listing=instance, amenity_names=amenity_names, **validated)
        output = ListingDetailSerializer(listing, context=self.get_serializer_context())
        return success_response(output.data, message="Listing updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return success_response(message="Listing deleted successfully.", status_code=200)


class ListingImageUploadView(APIView):
    """POST /api/v1/listings/{public_id}/images/ - upload a gallery image (owner/Admin only)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ListingImageUploadSerializer

    def post(self, request, public_id):
        listing = get_object_or_404(Listing, public_id=public_id)
        self._check_ownership(request, listing)

        serializer = ListingImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            image = services.add_listing_image(
                listing=listing,
                image_file=serializer.validated_data["image"],
                is_main=serializer.validated_data.get("is_main", False),
            )
        except DjangoValidationError as exc:
            raise ValidationError({"image": exc.messages if hasattr(exc, "messages") else str(exc)})

        return success_response(
            ListingImageSerializer(image, context={"request": request}).data,
            message="Image uploaded successfully.",
            status_code=201,
        )

    @staticmethod
    def _check_ownership(request, listing):
        if request.user.role == request.user.Role.ADMIN:
            return
        if request.user.role == request.user.Role.STAFF and listing.realtor_id == request.user.id:
            return
        raise PermissionDenied("You may only manage images on your own listings.")


class ListingImageDeleteView(APIView):
    """DELETE /api/v1/listings/{public_id}/images/{image_id}/ - remove a gallery image."""

    permission_classes = [IsAuthenticated]
    serializer_class = None  # no request body; DELETE only

    def delete(self, request, public_id, image_id):
        listing = get_object_or_404(Listing, public_id=public_id)
        ListingImageUploadView._check_ownership(request, listing)
        listing_image = get_object_or_404(ListingImage, id=image_id, listing=listing)
        services.delete_listing_image(listing_image=listing_image)
        return success_response(message="Image deleted successfully.")
