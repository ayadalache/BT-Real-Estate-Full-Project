import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.listings.constants import US_STATE_CHOICES


class Amenity(models.Model):
    """
    Normalized feature/amenity (Pool, Garage, Fireplace, etc). Modeled as its
    own table + M2M rather than a free-text column so the "Keyword" search
    box matches precisely instead of doing fragile substring matching over a
    blob of text, and so amenities can be managed/renamed in one place.
    """

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        db_table = "amenities"
        verbose_name_plural = "amenities"
        ordering = ["name"]

    def __str__(self):
        return self.name


def listing_image_upload_path(instance, filename):
    """
    Random filename (never trust user-supplied names): prevents directory
    traversal via crafted filenames and avoids leaking any information about
    the uploader's original file. Extension is preserved (already validated
    in validators.py before this is ever called) so browsers still render it
    correctly.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    random_name = f"{uuid.uuid4().hex}.{ext}"
    return f"listings/{instance.listing_id}/{random_name}"


class Listing(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PENDING = "PENDING", "Pending"
        SOLD = "SOLD", "Sold"
        RENTED = "RENTED", "Rented"
        INACTIVE = "INACTIVE", "Inactive"

    class ListingType(models.TextChoices):
        SALE = "SALE", "For Sale"
        RENT = "RENT", "For Rent"

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    title = models.CharField(max_length=200)
    address_line = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=2, choices=US_STATE_CHOICES, db_index=True)
    zip_code = models.CharField(max_length=10)

    listing_type = models.CharField(max_length=10, choices=ListingType.choices, default=ListingType.RENT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    bedrooms = models.PositiveSmallIntegerField(validators=[MaxValueValidator(50)])
    bathrooms = models.DecimalField(
        max_digits=3, decimal_places=1, validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    garage_spaces = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(20)])
    square_feet = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    lot_size_acres = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )

    description = models.TextField(blank=True)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="listings")

    realtor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # never silently orphan listings if a realtor account is deleted
        related_name="listings",
        limit_choices_to={"role__in": ["ADMIN", "STAFF"]},
    )

    listing_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "listings"
        ordering = ["-listing_date", "-created_at"]
        indexes = [
            models.Index(fields=["city", "state"]),
            models.Index(fields=["status", "listing_type"]),
            models.Index(fields=["price"]),
            models.Index(fields=["bedrooms"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="listing_price_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.city}, {self.state}"

    @property
    def main_image(self):
        return self.images.filter(is_main=True).first() or self.images.first()


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=listing_image_upload_path)
    is_main = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "listing_images"
        ordering = ["display_order", "uploaded_at"]
        indexes = [models.Index(fields=["listing", "is_main"])]

    def __str__(self):
        return f"Image for {self.listing_id} (main={self.is_main})"
