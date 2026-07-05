from rest_framework import serializers

from apps.inquiries.models import Inquiry
from apps.inquiries.validators import phone_regex, validate_message_content
from apps.listings.models import Listing
from apps.users.serializers import UserPublicSerializer


class ListingMiniSerializer(serializers.ModelSerializer):
    """Minimal listing info for embedding in inquiry/dashboard responses."""

    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = ["public_id", "title", "address_line", "city", "state", "main_image"]
        read_only_fields = fields

    def get_main_image(self, obj) -> str | None:
        image = obj.main_image
        if not image:
            return None
        request = self.context.get("request")
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class InquiryCreateSerializer(serializers.Serializer):
    """
    Public-facing serializer for the "Make An Inquiry" form. Accepts the
    listing by its public UUID (never the internal integer PK) and only
    matches listings that are currently ACTIVE — you cannot inquire about a
    pending/sold/inactive listing.
    """

    listing = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Listing.objects.filter(status=Listing.Status.ACTIVE),
    )
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=17, required=False, allow_blank=True, validators=[phone_regex])
    message = serializers.CharField(max_length=2000)

    def validate_message(self, value):
        return validate_message_content(value)


class InquirySerializer(serializers.ModelSerializer):
    """Full representation for a listing's realtor / Admin inbox."""

    listing = ListingMiniSerializer(read_only=True)
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Inquiry
        fields = ["id", "listing", "user", "name", "email", "phone", "message", "status", "created_at"]
        read_only_fields = fields


class InquiryStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ["status"]


class DashboardInquirySerializer(serializers.ModelSerializer):
    """Row shape for the "listings you've inquired about" dashboard table."""

    listing = ListingMiniSerializer(read_only=True)

    class Meta:
        model = Inquiry
        fields = ["id", "listing", "status", "created_at"]
        read_only_fields = fields
