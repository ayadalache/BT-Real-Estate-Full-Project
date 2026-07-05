from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

VALID_PASSWORD = "Str0ng!Passw0rd"


class MyProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser", email="profile@example.com", password=VALID_PASSWORD,
            first_name="Pro", last_name="File", is_email_verified=True, role=User.Role.USER,
        )
        login = self.client.post(
            reverse("authentication:login"), {"username": "profileuser", "password": VALID_PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
        self.url = reverse("users:my-profile")

    def test_retrieve_own_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], "profile@example.com")

    def test_update_editable_field(self):
        response = self.client.patch(self.url, {"first_name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")

    def test_cannot_escalate_role_via_profile_update(self):
        """Mass-assignment protection: role is read-only on this serializer."""
        response = self.client.patch(self.url, {"role": "ADMIN"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.USER)

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyProfilePhotoTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="photouser", email="photouser@example.com", password=VALID_PASSWORD,
            is_email_verified=True,
        )
        login = self.client.post(
            reverse("authentication:login"), {"username": "photouser", "password": VALID_PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
        self.url = reverse("users:my-profile-photo")

    @staticmethod
    def _make_image():
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (50, 50), color="blue").save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile("avatar.jpg", buf.read(), content_type="image/jpeg")

    def test_upload_valid_photo(self):
        response = self.client.post(self.url, {"photo": self._make_image()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_photo))

    def test_reupload_replaces_previous_photo(self):
        self.client.post(self.url, {"photo": self._make_image()}, format="multipart")
        self.user.refresh_from_db()
        first_name = self.user.profile_photo.name
        self.client.post(self.url, {"photo": self._make_image()}, format="multipart")
        self.user.refresh_from_db()
        self.assertNotEqual(first_name, self.user.profile_photo.name)

    def test_rejects_disguised_non_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile("avatar.jpg", b"not-an-image", content_type="image/jpeg")
        response = self.client.post(self.url, {"photo": fake}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(self.url, {"photo": self._make_image()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
