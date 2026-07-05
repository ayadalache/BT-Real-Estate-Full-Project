import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from apps.users.managers import UserManager


def user_photo_upload_path(instance, filename):
    """Random filename, mirroring the listings image upload convention (see apps.listings.models)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"profile_photos/{uuid.uuid4().hex}.{ext}"


class User(AbstractUser):
    """
    Custom user model. We extend AbstractUser (rather than AbstractBaseUser)
    to keep Django's battle-tested username/permission machinery, while
    adding the fields our platform needs: a public UUID (never expose
    sequential integer PKs in URLs — avoids enumeration of users), an RBAC
    role, and email verification state.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"  # realtors: only role (besides Admin) allowed to manage listings
        USER = "USER", "User"

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER, db_index=True)

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)

    is_email_verified = models.BooleanField(default=False)

    bio = models.TextField(max_length=1000, blank=True)
    profile_photo = models.ImageField(upload_to=user_photo_upload_path, blank=True, null=True)

    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff_role(self):
        return self.role == self.Role.STAFF
