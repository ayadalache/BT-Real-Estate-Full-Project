import io

from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.listings.models import Amenity, Listing, ListingImage
from apps.users.models import User

VALID_PASSWORD = "Str0ng!Passw0rd"


def make_test_image(fmt="JPEG", content_type="image/jpeg", name="test.jpg", size=(100, 100)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color="red").save(buffer, format=fmt)
    buffer.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


class ListingTestBase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1", email="admin1@example.com", password=VALID_PASSWORD,
            role=User.Role.ADMIN, is_email_verified=True,
        )
        self.staff1 = User.objects.create_user(
            username="staff1", email="staff1@example.com", password=VALID_PASSWORD,
            role=User.Role.STAFF, is_email_verified=True,
        )
        self.staff2 = User.objects.create_user(
            username="staff2", email="staff2@example.com", password=VALID_PASSWORD,
            role=User.Role.STAFF, is_email_verified=True,
        )
        self.regular_user = User.objects.create_user(
            username="user1", email="user1@example.com", password=VALID_PASSWORD,
            role=User.Role.USER, is_email_verified=True,
        )

    def auth_as(self, user):
        login = self.client.post(
            reverse("authentication:login"), {"username": user.username, "password": VALID_PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")

    def make_listing(self, realtor=None, status_=Listing.Status.ACTIVE, **overrides):
        defaults = dict(
            title="Cozy 3BR House", address_line="123 Main St", city="Boston", state="MA",
            zip_code="02108", listing_type=Listing.ListingType.RENT, status=status_,
            price="2500.00", bedrooms=3, bathrooms="2.0", garage_spaces=1,
            square_feet=1500, lot_size_acres="0.25", description="A lovely home.",
            listing_date="2026-01-01", realtor=realtor or self.staff1,
        )
        defaults.update(overrides)
        return Listing.objects.create(**defaults)


class ListingListRetrieveTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.active = self.make_listing(title="Active Listing")
        self.pending = self.make_listing(title="Pending Listing", status_=Listing.Status.PENDING)
        self.list_url = reverse("listings:listing-list")

    def test_anonymous_sees_only_active_listings(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Active Listing", titles)
        self.assertNotIn("Pending Listing", titles)

    def test_owning_staff_sees_own_pending_listing(self):
        self.auth_as(self.staff1)
        response = self.client.get(self.list_url)
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Pending Listing", titles)

    def test_other_staff_does_not_see_pending_listing(self):
        self.auth_as(self.staff2)
        response = self.client.get(self.list_url)
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertNotIn("Pending Listing", titles)

    def test_admin_sees_all_listings(self):
        self.auth_as(self.admin)
        response = self.client.get(self.list_url)
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Pending Listing", titles)

    def test_anonymous_cannot_retrieve_pending_listing_detail(self):
        """
        Returns 404 rather than 403: the queryset already excludes non-active
        listings for anonymous users, so no pending/inactive listing's
        existence is ever confirmed to an unauthenticated caller.
        """
        url = reverse("listings:listing-detail", kwargs={"public_id": self.pending.public_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_retrieve_own_pending_listing_detail(self):
        self.auth_as(self.staff1)
        url = reverse("listings:listing-detail", kwargs={"public_id": self.pending.public_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ListingFilterSearchTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.house_a = self.make_listing(
            title="Lakeside Cottage", city="Austin", state="TX", bedrooms=2, price="1800.00"
        )
        self.house_b = self.make_listing(
            title="Downtown Loft", city="Austin", state="TX", bedrooms=4, price="3500.00"
        )
        self.house_a.amenities.set([Amenity.objects.create(name="Pool", slug="pool")])
        self.list_url = reverse("listings:listing-list")

    def test_filter_by_city(self):
        response = self.client.get(self.list_url, {"city": "Austin"})
        self.assertEqual(len(response.data["data"]["results"]), 2)

    def test_filter_by_max_price(self):
        response = self.client.get(self.list_url, {"max_price": "2000"})
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Lakeside Cottage", titles)
        self.assertNotIn("Downtown Loft", titles)

    def test_filter_by_min_bedrooms(self):
        response = self.client.get(self.list_url, {"min_bedrooms": "3"})
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Downtown Loft", titles)
        self.assertNotIn("Lakeside Cottage", titles)

    def test_keyword_search_matches_amenity(self):
        response = self.client.get(self.list_url, {"search": "Pool"})
        titles = [r["title"] for r in response.data["data"]["results"]]
        self.assertIn("Lakeside Cottage", titles)
        self.assertNotIn("Downtown Loft", titles)


class ListingCreateTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("listings:listing-list")
        self.payload = {
            "title": "New Build", "address_line": "1 New St", "city": "Denver", "state": "CO",
            "zip_code": "80202", "listing_type": "RENT", "status": "ACTIVE",
            "price": "2200.00", "bedrooms": 3, "bathrooms": "2.0", "garage_spaces": 2,
            "square_feet": 1600, "lot_size_acres": "0.3", "description": "Brand new.",
            "listing_date": "2026-02-01", "amenity_names": ["Garage", "Pool"],
        }

    def test_regular_user_cannot_create_listing(self):
        self.auth_as(self.regular_user)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_listing(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_can_create_listing_owned_by_self(self):
        self.auth_as(self.staff1)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing = Listing.objects.get(title="New Build")
        self.assertEqual(listing.realtor, self.staff1)
        self.assertEqual(listing.amenities.count(), 2)

    def test_staff_cannot_assign_listing_to_another_realtor(self):
        self.auth_as(self.staff1)
        payload = dict(self.payload, realtor_id=self.staff2.id)
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_assign_listing_to_a_realtor(self):
        self.auth_as(self.admin)
        payload = dict(self.payload, realtor_id=self.staff2.id)
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing = Listing.objects.get(title="New Build")
        self.assertEqual(listing.realtor, self.staff2)

    def test_negative_price_rejected(self):
        self.auth_as(self.staff1)
        payload = dict(self.payload, price="-100.00")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ListingUpdateDeleteTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.listing = self.make_listing(realtor=self.staff1)
        self.url = reverse("listings:listing-detail", kwargs={"public_id": self.listing.public_id})

    def test_owner_can_update_own_listing(self):
        self.auth_as(self.staff1)
        response = self.client.patch(self.url, {"price": "2600.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(str(self.listing.price), "2600.00")

    def test_other_staff_cannot_update_listing(self):
        self.auth_as(self.staff2)
        response = self.client.patch(self.url, {"price": "2600.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_listing(self):
        self.auth_as(self.admin)
        response = self.client.patch(self.url, {"price": "2700.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_delete_own_listing(self):
        self.auth_as(self.staff1)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_regular_user_cannot_delete_listing(self):
        self.auth_as(self.regular_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ListingImageUploadTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.listing = self.make_listing(realtor=self.staff1)
        self.url = reverse(
            "listings:listing-image-upload", kwargs={"public_id": self.listing.public_id}
        )

    def test_owner_can_upload_valid_image(self):
        self.auth_as(self.staff1)
        response = self.client.post(self.url, {"image": make_test_image(), "is_main": True}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.listing.images.count(), 1)
        self.assertTrue(self.listing.images.first().is_main)

    def test_first_image_becomes_main_automatically(self):
        self.auth_as(self.staff1)
        self.client.post(self.url, {"image": make_test_image()}, format="multipart")
        self.assertTrue(self.listing.images.first().is_main)

    def test_other_staff_cannot_upload_image(self):
        self.auth_as(self.staff2)
        response = self.client.post(self.url, {"image": make_test_image()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_disguised_non_image_file(self):
        """A .jpg-named file containing executable-looking content must be rejected."""
        self.auth_as(self.staff1)
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile("malicious.jpg", b"<?php system($_GET['c']); ?>", content_type="image/jpeg")
        response = self.client.post(self.url, {"image": fake}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.listing.images.count(), 0)

    def test_rejects_disallowed_extension(self):
        self.auth_as(self.staff1)
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="GIF")
        buf.seek(0)
        from django.core.files.uploadedfile import SimpleUploadedFile
        gif = SimpleUploadedFile("image.gif", buf.read(), content_type="image/gif")
        response = self.client.post(self.url, {"image": gif}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_uploaded_image_gets_random_filename(self):
        self.auth_as(self.staff1)
        self.client.post(self.url, {"image": make_test_image(name="original_name.jpg")}, format="multipart")
        stored_name = self.listing.images.first().image.name
        self.assertNotIn("original_name", stored_name)

    def test_delete_image(self):
        self.auth_as(self.staff1)
        self.client.post(self.url, {"image": make_test_image()}, format="multipart")
        image = self.listing.images.first()
        delete_url = reverse(
            "listings:listing-image-delete",
            kwargs={"public_id": self.listing.public_id, "image_id": image.id},
        )
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.listing.images.count(), 0)
