"""
Business logic for the authentication flow, kept out of views/serializers so
views stay thin and this logic is independently unit-testable.

Email verification and password-reset tokens are stateless, signed tokens
(HMAC via Django's signing framework) rather than DB-stored tokens: this
avoids an extra table + cleanup job, they cannot be forged without
SECRET_KEY, and they self-expire via `max_age`. Each token is scoped with a
distinct "salt" (purpose) so a verification token can never be replayed as a
password-reset token.
"""
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils.html import strip_tags

from apps.users.models import User

logger = logging.getLogger("apps")
security_logger = logging.getLogger("security")

EMAIL_VERIFICATION_SALT = "auth.email-verification"
PASSWORD_RESET_SALT = "auth.password-reset"


class TokenExpiredOrInvalid(Exception):
    pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@transaction.atomic
def register_user(*, username, email, password, first_name, last_name, phone_number="") -> User:
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=User.Role.USER,
        is_active=True,
        is_email_verified=False,
    )
    send_verification_email(user)
    logger.info("New user registered: %s", user.public_id)
    return user


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
def _make_token(user: User, salt: str) -> str:
    return signing.dumps({"uid": str(user.public_id)}, salt=salt)


def _read_token(token: str, salt: str, max_age_seconds: int) -> User:
    try:
        payload = signing.loads(token, salt=salt, max_age=max_age_seconds)
    except signing.SignatureExpired:
        raise TokenExpiredOrInvalid("This link has expired. Please request a new one.")
    except signing.BadSignature:
        raise TokenExpiredOrInvalid("This link is invalid.")

    try:
        return User.objects.get(public_id=payload["uid"])
    except (User.DoesNotExist, KeyError):
        raise TokenExpiredOrInvalid("This link is invalid.")


def send_verification_email(user: User) -> None:
    token = _make_token(user, EMAIL_VERIFICATION_SALT)
    verify_url = f"{settings.FRONTEND_URL}/verify-email.html?token={token}"

    subject = "Verify your BT Real Estate account"
    html_message = (
        f"<p>Hi {user.first_name or user.username},</p>"
        f"<p>Please verify your email by clicking the link below "
        f"(expires in {settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS} hours):</p>"
        f'<p><a href="{verify_url}">{verify_url}</a></p>'
    )
    _send_email(subject, html_message, [user.email])


def verify_email(token: str) -> User:
    user = _read_token(
        token,
        EMAIL_VERIFICATION_SALT,
        settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS * 3600,
    )
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])
        logger.info("Email verified for user: %s", user.public_id)
    return user


def resend_verification_email(user: User) -> None:
    if user.is_email_verified:
        return
    send_verification_email(user)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
def send_password_reset_email(user: User) -> None:
    token = _make_token(user, PASSWORD_RESET_SALT)
    reset_url = f"{settings.FRONTEND_URL}/reset-password.html?token={token}"

    subject = "Reset your BT Real Estate password"
    html_message = (
        f"<p>Hi {user.first_name or user.username},</p>"
        f"<p>We received a request to reset your password. This link expires in "
        f"{settings.PASSWORD_RESET_TOKEN_TTL_HOURS} hour(s):</p>"
        f'<p><a href="{reset_url}">{reset_url}</a></p>'
        f"<p>If you did not request this, you can safely ignore this email.</p>"
    )
    _send_email(subject, html_message, [user.email])


def request_password_reset(email: str) -> None:
    """
    Deliberately does not reveal whether the email exists (prevents user
    enumeration). Always behaves the same way to the caller.
    """
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        security_logger.info("Password reset requested for unknown email.")
        return
    send_password_reset_email(user)
    security_logger.info("Password reset requested for user: %s", user.public_id)


@transaction.atomic
def confirm_password_reset(token: str, new_password: str) -> User:
    user = _read_token(
        token,
        PASSWORD_RESET_SALT,
        settings.PASSWORD_RESET_TOKEN_TTL_HOURS * 3600,
    )
    user.set_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(update_fields=["password", "failed_login_attempts", "locked_until", "updated_at"])
    security_logger.info("Password reset completed for user: %s", user.public_id)
    return user


@transaction.atomic
def change_password(user: User, new_password: str) -> None:
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    security_logger.info("Password changed for user: %s", user.public_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _send_email(subject: str, html_message: str, recipient_list: list[str]) -> None:
    send_mail(
        subject=subject,
        message=strip_tags(html_message),
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )
