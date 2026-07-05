from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inquiries.models import Inquiry
from apps.listings.models import Listing
from apps.users.models import User

VALID_PASSWORD = "Str0ng!Passw0rd"


class InquiryTestBase(APITestCase):
    def setUp(self):
        self.staff1 = User.objects.create_user(
            username="realtor1", email="realtor1@example.com", password=VALID_PASSWORD,
            role=User.Role.STAFF, is_email_verified=True,
        )
        self.staff2 = User.objects.create_user(
            username="realtor2", email="realtor2@example.com", password=VALID_PASSWORD,
            role=User.Role.STAFF, is_email_verified=True,
        )
        self.admin = User.objects.create_user(
            username="admin1", email="admin1@example.com", password=VALID_PASSWORD,
            role=User.Role.ADMIN, is_email_verified=True,
        )
        self.buyer = User.objects.create_user(
            username="buyer1", email="buyer1@example.com", password=VALID_PASSWORD,
            role=User.Role.USER, is_email_verified=True,
        )
        self.active_listing = Listing.objects.create(
            title="Sunny Duplex", address_line="45 Drivewood Circle", city="Boston", state="MA",
            zip_code="02108", listing_type=Listing.ListingType.RENT, status=Listing.Status.ACTIVE,
            price="2500.00", bedrooms=3, bathrooms="2.0", garage_spaces=1,
            square_feet=1500, listing_date="2026-01-01", realtor=self.staff1,
        )
        self.pending_listing = Listing.objects.create(
            title="Draft Listing", address_line="1 Draft Way", city="Boston", state="MA",
            zip_code="02108", listing_type=Listing.ListingType.RENT, status=Listing.Status.PENDING,
            price="2000.00", bedrooms=2, bathrooms="1.0", garage_spaces=0,
            square_feet=1000, listing_date="2026-01-01", realtor=self.staff1,
        )

    def auth_as(self, user):
        login = self.client.post(
            reverse("authentication:login"), {"username": user.username, "password": VALID_PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")


class InquiryCreateTests(InquiryTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("inquiries:inquiry-create")
        self.payload = {
            "listing": str(self.active_listing.public_id),
            "name": "Jane Prospect",
            "email": "jane.prospect@example.com",
            "phone": "+16175551234",
            "message": "Is this property still available for rent?",
        }

    def test_guest_can_submit_inquiry(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inquiry = Inquiry.objects.get(email="jane.prospect@example.com")
        self.assertIsNone(inquiry.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.staff1.email])

    def test_authenticated_user_inquiry_is_linked_to_account(self):
        self.auth_as(self.buyer)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inquiry = Inquiry.objects.get(email="jane.prospect@example.com")
        self.assertEqual(inquiry.user, self.buyer)

    def test_cannot_inquire_about_non_active_listing(self):
        payload = dict(self.payload, listing=str(self.pending_listing.public_id))
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_too_short_message(self):
        payload = dict(self.payload, message="Hi")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_phone_format(self):
        payload = dict(self.payload, phone="not-a-phone")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_unknown_listing(self):
        payload = dict(self.payload, listing="00000000-0000-0000-0000-000000000000")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InquiryInboxTests(InquiryTestBase):
    def setUp(self):
        super().setUp()
        self.inquiry1 = Inquiry.objects.create(
            listing=self.active_listing, name="A", email="a@example.com", message="Interested in viewing."
        )
        other_listing = Listing.objects.create(
            title="Other Listing", address_line="2 Other St", city="Boston", state="MA",
            zip_code="02108", listing_type=Listing.ListingType.RENT, status=Listing.Status.ACTIVE,
            price="1800.00", bedrooms=2, bathrooms="1.0", garage_spaces=0,
            square_feet=900, listing_date="2026-01-01", realtor=self.staff2,
        )
        self.inquiry2 = Inquiry.objects.create(
            listing=other_listing, name="B", email="b@example.com", message="Another inquiry here."
        )
        self.url = reverse("inquiries:inquiry-inbox")

    def test_realtor_sees_only_own_listing_inquiries(self):
        self.auth_as(self.staff1)
        response = self.client.get(self.url)
        ids = [r["id"] for r in response.data["data"]["results"]]
        self.assertIn(self.inquiry1.id, ids)
        self.assertNotIn(self.inquiry2.id, ids)

    def test_admin_sees_all_inquiries(self):
        self.auth_as(self.admin)
        response = self.client.get(self.url)
        ids = [r["id"] for r in response.data["data"]["results"]]
        self.assertIn(self.inquiry1.id, ids)
        self.assertIn(self.inquiry2.id, ids)

    def test_regular_user_cannot_access_inbox(self):
        self.auth_as(self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_access_inbox(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class InquiryDetailTests(InquiryTestBase):
    def setUp(self):
        super().setUp()
        self.inquiry = Inquiry.objects.create(
            listing=self.active_listing, name="A", email="a@example.com", message="Interested in viewing."
        )
        self.url = reverse("inquiries:inquiry-detail", kwargs={"pk": self.inquiry.pk})

    def test_owning_realtor_can_view(self):
        self.auth_as(self.staff1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_realtor_cannot_view(self):
        self.auth_as(self.staff2)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owning_realtor_can_update_status(self):
        self.auth_as(self.staff1)
        response = self.client.patch(self.url, {"status": "CONTACTED"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, "CONTACTED")

    def test_invalid_status_rejected(self):
        self.auth_as(self.staff1)
        response = self.client.patch(self.url, {"status": "BOGUS"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DashboardTests(InquiryTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("inquiries:dashboard")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_shows_only_own_inquiries(self):
        Inquiry.objects.create(
            listing=self.active_listing, user=self.buyer, name="Buyer One",
            email="buyer1@example.com", message="Can I schedule a tour?",
        )
        Inquiry.objects.create(
            listing=self.active_listing, name="Someone Else",
            email="other@example.com", message="Guest inquiry not linked to buyer.",
        )
        self.auth_as(self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["listing"]["title"], "Sunny Duplex")
