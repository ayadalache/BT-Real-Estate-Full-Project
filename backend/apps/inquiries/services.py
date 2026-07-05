import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.html import strip_tags

from apps.inquiries.models import Inquiry
from apps.listings.models import Listing

logger = logging.getLogger("apps")


@transaction.atomic
def create_inquiry(*, listing: Listing, name: str, email: str, phone: str, message: str, user=None) -> Inquiry:
    inquiry = Inquiry.objects.create(
        listing=listing, user=user, name=name, email=email, phone=phone, message=message,
    )
    _notify_realtor(inquiry)
    logger.info("Inquiry created on listing %s", listing.public_id)
    return inquiry


def _notify_realtor(inquiry: Inquiry) -> None:
    realtor = inquiry.listing.realtor
    subject = f"New inquiry: {inquiry.listing.title}"
    html_message = (
        f"<p>You have a new inquiry on <strong>{inquiry.listing.title}</strong> "
        f"({inquiry.listing.address_line}, {inquiry.listing.city}, {inquiry.listing.state}).</p>"
        f"<p><strong>From:</strong> {inquiry.name} ({inquiry.email}"
        f"{', ' + inquiry.phone if inquiry.phone else ''})</p>"
        f"<p><strong>Message:</strong><br>{inquiry.message}</p>"
    )
    send_mail(
        subject=subject,
        message=strip_tags(html_message),
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[realtor.email],
        fail_silently=False,
    )


def get_dashboard_inquiries(user):
    """Listings the given user has personally inquired about (dashboard.html)."""
    return (
        Inquiry.objects.filter(user=user)
        .select_related("listing")
        .prefetch_related("listing__images")
        .order_by("-created_at")
    )


def get_realtor_inbox(user):
    """Inquiries received on listings owned by `user` (Admins see every inquiry)."""
    queryset = Inquiry.objects.select_related("listing", "user").order_by("-created_at")
    if user.role == user.Role.ADMIN:
        return queryset
    return queryset.filter(listing__realtor=user)


@transaction.atomic
def update_inquiry_status(*, inquiry: Inquiry, status: str) -> Inquiry:
    inquiry.status = status
    inquiry.save(update_fields=["status", "updated_at"])
    return inquiry
