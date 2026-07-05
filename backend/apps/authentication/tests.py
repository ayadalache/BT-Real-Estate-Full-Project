from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication import services
from apps.users.models import User

VALID_PASSWORD = "Str0ng!Passw0rd"


class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("authentication:register")
        self.payload = {
            "first_name": "Kyle",
            "last_name": "Brown",
            "username": "kylebrown",
            "email": "kyle@example.com",
            "password": VALID_PASSWORD,
            "password2": VALID_PASSWORD,
        }

    def test_register_success_creates_inactive_verification_user(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        user = User.objects.get(email="kyle@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.role, User.Role.USER)
        # Password must never be stored/returned in plaintext
        self.assertNotIn("password", response.data["data"]["user"])
        self.assertEqual(len(mail.outbox), 1)

    def test_register_rejects_weak_password(self):
        self.payload["password"] = "password"
        self.payload["password2"] = "password"
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_register_rejects_mismatched_passwords(self):
        self.payload["password2"] = "Different!123"
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_duplicate_email(self):
        self.client.post(self.url, self.payload)
        second = dict(self.payload, username="anotherusername")
        response = self.client.post(self.url, second)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_reserved_username(self):
        self.payload["username"] = "admin"
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_invalid_input_types_mass_assignment(self):
        """Ensure role cannot be injected via the registration payload."""
        payload = dict(self.payload, role="ADMIN")
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="kyle@example.com")
        self.assertEqual(user.role, User.Role.USER)  # role field silently ignored


class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe", email="jane@example.com", password=VALID_PASSWORD,
            first_name="Jane", last_name="Doe",
        )

    def test_verify_email_with_valid_token(self):
        token = services._make_token(self.user, services.EMAIL_VERIFICATION_SALT)
        response = self.client.post(reverse("authentication:verify-email"), {"token": token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_email_with_invalid_token(self):
        response = self.client.post(reverse("authentication:verify-email"), {"token": "garbage"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verification_token_cannot_be_used_as_reset_token(self):
        """A token minted for one purpose must not work for another (salt scoping)."""
        verify_token = services._make_token(self.user, services.EMAIL_VERIFICATION_SALT)
        with self.assertRaises(services.TokenExpiredOrInvalid):
            services._read_token(verify_token, services.PASSWORD_RESET_SALT, 3600)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="verifieduser", email="verified@example.com", password=VALID_PASSWORD,
            first_name="Ver", last_name="Fied", is_email_verified=True,
        )
        self.url = reverse("authentication:login")

    def test_login_success_returns_tokens(self):
        response = self.client.post(self.url, {"username": "verifieduser", "password": VALID_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])

    def test_login_fails_unverified_email(self):
        User.objects.create_user(
            username="unverified", email="unverified@example.com", password=VALID_PASSWORD,
        )
        response = self.client.post(self.url, {"username": "unverified", "password": VALID_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_fails_wrong_password(self):
        response = self.client.post(self.url, {"username": "verifieduser", "password": "WrongPass!1"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_locks_after_max_failed_attempts(self):
        for _ in range(5):
            self.client.post(self.url, {"username": "verifieduser", "password": "WrongPass!1"})
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)
        self.assertGreater(self.user.locked_until, timezone.now())

        # Even the correct password is now rejected while locked
        response = self.client.post(self.url, {"username": "verifieduser", "password": VALID_PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_login_resets_failed_attempts(self):
        self.client.post(self.url, {"username": "verifieduser", "password": "WrongPass!1"})
        self.client.post(self.url, {"username": "verifieduser", "password": VALID_PASSWORD})
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)


class TokenLifecycleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tokenuser", email="token@example.com", password=VALID_PASSWORD,
            is_email_verified=True,
        )
        login = self.client.post(
            reverse("authentication:login"), {"username": "tokenuser", "password": VALID_PASSWORD}
        )
        self.access = login.data["data"]["access"]
        self.refresh = login.data["data"]["refresh"]

    def test_refresh_returns_new_access_token(self):
        response = self.client.post(reverse("authentication:refresh"), {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["data"])

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get(reverse("authentication:me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_with_valid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.get(reverse("authentication:me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], "token@example.com")

    def test_logout_blacklists_refresh_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.post(reverse("authentication:logout"), {"refresh": self.refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempting to use the blacklisted refresh token must fail
        response2 = self.client.post(reverse("authentication:refresh"), {"refresh": self.refresh})
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="resetuser", email="reset@example.com", password=VALID_PASSWORD,
            is_email_verified=True,
        )

    def test_request_reset_always_returns_generic_success(self):
        # Existing email
        r1 = self.client.post(reverse("authentication:password-reset"), {"email": "reset@example.com"})
        # Non-existent email
        r2 = self.client.post(reverse("authentication:password-reset"), {"email": "nobody@example.com"})
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.data["message"], r2.data["message"])  # identical -> no enumeration
        self.assertEqual(len(mail.outbox), 1)  # only sent for the real user

    def test_confirm_reset_with_valid_token_changes_password(self):
        token = services._make_token(self.user, services.PASSWORD_RESET_SALT)
        new_password = "NewStr0ng!Pass"
        response = self.client.post(
            reverse("authentication:password-reset-confirm"),
            {"token": token, "new_password": new_password, "new_password2": new_password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_confirm_reset_with_invalid_token_fails(self):
        response = self.client.post(
            reverse("authentication:password-reset-confirm"),
            {"token": "bad-token", "new_password": "NewStr0ng!Pass", "new_password2": "NewStr0ng!Pass"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="changeuser", email="change@example.com", password=VALID_PASSWORD,
            is_email_verified=True,
        )
        login = self.client.post(
            reverse("authentication:login"), {"username": "changeuser", "password": VALID_PASSWORD}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['access']}")
        self.url = reverse("authentication:change-password")

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {"current_password": VALID_PASSWORD, "new_password": "AnotherStr0ng!1", "new_password2": "AnotherStr0ng!1"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("AnotherStr0ng!1"))

    def test_change_password_wrong_current_password(self):
        response = self.client.post(
            self.url,
            {"current_password": "WrongOne!1", "new_password": "AnotherStr0ng!1", "new_password2": "AnotherStr0ng!1"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(
            self.url,
            {"current_password": VALID_PASSWORD, "new_password": "AnotherStr0ng!1", "new_password2": "AnotherStr0ng!1"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
