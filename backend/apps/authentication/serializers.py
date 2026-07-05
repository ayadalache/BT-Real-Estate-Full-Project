import logging

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed as DRFAuthenticationFailed
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.authentication.validators import validate_username
from apps.users.models import User
from apps.users.serializers import UserProfileSerializer

security_logger = logging.getLogger("security")

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})
    phone_number = serializers.CharField(max_length=17, required=False, allow_blank=True)

    def validate_username(self, value):
        validate_username(value)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            # Same generic wording used everywhere to avoid account enumeration
            raise serializers.ValidationError("Unable to register with the provided details.")
        return value

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs


class RegisterResponseSerializer(serializers.Serializer):
    """Read-only shape returned after successful registration."""
    user = UserProfileSerializer()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends SimpleJWT's serializer to:
    - block login for unverified / inactive / locked-out accounts
    - support a `remember_me` flag that extends refresh token lifetime
    - embed non-sensitive claims (role) directly in the access token so the
      frontend/downstream services can read role without an extra API call
    """

    remember_me = serializers.BooleanField(required=False, default=False, write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email_verified"] = user.is_email_verified
        return token

    def validate(self, attrs):
        username = attrs.get(self.username_field)
        candidate = User.objects.filter(**{f"{self.username_field}__iexact": username}).first()

        if candidate and candidate.locked_until and candidate.locked_until > timezone.now():
            security_logger.warning("Login blocked (account locked): %s", candidate.public_id)
            raise AuthenticationFailed(
                "Account temporarily locked due to repeated failed login attempts. "
                "Please try again later or reset your password."
            )

        try:
            data = super().validate(attrs)
        except DRFAuthenticationFailed:
            if candidate:
                self._register_failed_attempt(candidate)
            raise

        # Successful credential check: reset any failed-attempt counter.
        if candidate and candidate.failed_login_attempts:
            candidate.failed_login_attempts = 0
            candidate.locked_until = None
            candidate.save(update_fields=["failed_login_attempts", "locked_until"])

        if not self.user.is_active:
            raise AuthenticationFailed("This account has been deactivated.")

        if not self.user.is_email_verified:
            raise AuthenticationFailed("Please verify your email address before logging in.")

        remember_me = attrs.get("remember_me", False)
        if remember_me:
            refresh = data["refresh"]
            # `refresh` here is a plain string from super().validate(); re-derive the
            # token object only to adjust its lifetime for "remember me" sessions.
            from rest_framework_simplejwt.tokens import RefreshToken

            token_obj = RefreshToken(refresh)
            token_obj.set_exp(lifetime=settings.SIMPLE_JWT["REMEMBER_ME_REFRESH_TOKEN_LIFETIME"])
            data["refresh"] = str(token_obj)

        data["user"] = UserProfileSerializer(self.user).data
        return data

    @staticmethod
    def _register_failed_attempt(user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            security_logger.warning("Account locked after repeated failures: %s", user.public_id)
        user.save(update_fields=["failed_login_attempts", "locked_until"])


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "New password must differ from current password."})
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
