from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.users.serializers import UserProfileSerializer
from core.responses import success_response
from core.validators import validate_image_upload


class MyProfileView(RetrieveUpdateAPIView):
    """
    GET  /api/v1/users/me/  -> current user's profile
    PATCH/PUT /api/v1/users/me/ -> update editable profile fields only
    (role, email, verification status are read-only — see serializer).
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return success_response(serializer.data, message="Profile retrieved successfully.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, message="Profile updated successfully.")


class _PhotoUploadSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, value):
        validate_image_upload(value)
        return value


class MyProfilePhotoView(APIView):
    """POST /api/v1/users/me/photo/ - upload/replace the current user's profile photo."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = _PhotoUploadSerializer

    def post(self, request):
        serializer = _PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if user.profile_photo:
            user.profile_photo.delete(save=False)  # remove old file from storage before replacing
        user.profile_photo = serializer.validated_data["photo"]
        user.save(update_fields=["profile_photo", "updated_at"])

        return success_response(
            UserProfileSerializer(user, context={"request": request}).data,
            message="Profile photo updated successfully.",
        )
