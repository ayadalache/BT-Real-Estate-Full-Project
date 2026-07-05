from rest_framework import serializers

from apps.listings.models import Amenity, Listing, ListingImage
from apps.listings.validators import validate_image_upload
from apps.users.models import User
from apps.users.serializers import UserPublicSerializer


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "is_main", "display_order", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class ListingImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    is_main = serializers.BooleanField(required=False, default=False)

    def validate_image(self, value):
        validate_image_upload(value)
        return value


class ListingListSerializer(serializers.ModelSerializer):
    """Lightweight representation for listing cards (index/listings/search pages)."""

    main_image = serializers.SerializerMethodField()
    realtor = UserPublicSerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "public_id", "title", "address_line", "city", "state", "zip_code",
            "listing_type", "status", "price", "bedrooms", "bathrooms",
            "garage_spaces", "square_feet", "main_image", "realtor",
            "listing_date", "created_at",
        ]
        read_only_fields = fields

    def get_main_image(self, obj) -> str | None:
        image = obj.main_image
        if not image:
            return None
        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full representation for the single-listing detail page."""

    images = ListingImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    realtor = UserPublicSerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "public_id", "title", "address_line", "city", "state", "zip_code",
            "listing_type", "status", "price", "bedrooms", "bathrooms",
            "garage_spaces", "square_feet", "lot_size_acres", "description",
            "amenities", "images", "realtor", "listing_date", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ListingWriteSerializer(serializers.ModelSerializer):
    """
    Create/update serializer for Admin/Staff. Deliberately excludes `realtor`
    and `public_id` from client input:
    - `realtor` is set server-side by the view (defaults to the requesting
      staff member; only Admins may assign a different realtor) to prevent
      a staff member from creating listings attributed to someone else.
    - `amenities` is accepted as a plain list of names (`amenity_names`)
      rather than requiring the client to know internal Amenity IDs.
    """

    amenity_names = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, write_only=True
    )
    realtor_id = serializers.PrimaryKeyRelatedField(
        source="realtor",
        queryset=User.objects.filter(role__in=[User.Role.ADMIN, User.Role.STAFF]),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Listing
        fields = [
            "title", "address_line", "city", "state", "zip_code",
            "listing_type", "status", "price", "bedrooms", "bathrooms",
            "garage_spaces", "square_feet", "lot_size_acres", "description",
            "listing_date", "amenity_names", "realtor_id",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        # Only an Admin may assign/reassign the realtor on a listing.
        if "realtor" in attrs and request.user.role != request.user.Role.ADMIN:
            raise serializers.ValidationError(
                {"realtor_id": "Only administrators may assign a listing to a different realtor."}
            )
        return attrs
