from django.conf import settings
from django.db import models

from apps.listings.models import Listing


class Inquiry(models.Model):
    """
    A prospective tenant/buyer's message to a listing's realtor. `user` is
    nullable and populated automatically when the submitter is logged in
    (drives the "listings I've inquired about" dashboard) but guests may
    also submit inquiries without an account, matching the public
    "Make An Inquiry" modal on the listing detail page.
    """

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        CLOSED = "CLOSED", "Closed"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="inquiries")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=17, blank=True)
    message = models.TextField(max_length=2000)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inquiries"
        ordering = ["-created_at"]
        verbose_name_plural = "inquiries"
        indexes = [
            models.Index(fields=["listing", "status"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"Inquiry from {self.name} on listing {self.listing_id}"
