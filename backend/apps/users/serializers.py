from rest_framework import serializers

from apps.users.models import User


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Minimal, safe-to-expose representation of a user (e.g. as the realtor
    on a listing). Never includes email, phone, or any PII beyond a name;
    bio/photo are intentionally public since they're the realtor's own
    professional presentation shown on listing pages.
    """

    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["public_id", "first_name", "last_name", "role", "bio", "profile_photo"]
        read_only_fields = fields

    def get_profile_photo(self, obj) -> str | None:
        if not obj.profile_photo:
            return None
        request = self.context.get("request")
        url = obj.profile_photo.url
        return request.build_absolute_uri(url) if request else url


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full profile for the authenticated user themselves ("/me" endpoint).
    Sensitive/system-controlled fields are explicitly read-only so a user
    can never mass-assign their way into another role or verified state.
    `profile_photo` is read-only here too — it's set via the dedicated
    upload endpoint so it goes through image validation.
    """

    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "public_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "bio",
            "profile_photo",
            "role",
            "is_email_verified",
            "created_at",
        ]
        read_only_fields = ["public_id", "username", "email", "role", "is_email_verified", "profile_photo", "created_at"]

    def get_profile_photo(self, obj) -> str | None:
        if not obj.profile_photo:
            return None
        request = self.context.get("request")
        url = obj.profile_photo.url
        return request.build_absolute_uri(url) if request else url
