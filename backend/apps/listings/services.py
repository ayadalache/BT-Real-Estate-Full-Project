import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.listings.models import Amenity, Listing, ListingImage
from apps.listings.validators import MAX_IMAGES_PER_LISTING, validate_image_upload

logger = logging.getLogger("apps")


@transaction.atomic
def create_listing(*, realtor, amenity_names=None, **fields) -> Listing:
    listing = Listing(realtor=realtor, **fields)
    listing.full_clean(exclude=["amenities"])
    listing.save()
    if amenity_names:
        listing.amenities.set(_get_or_create_amenities(amenity_names))
    logger.info("Listing created: %s by realtor %s", listing.public_id, realtor.public_id)
    return listing


@transaction.atomic
def update_listing(*, listing: Listing, amenity_names=None, **fields) -> Listing:
    for field, value in fields.items():
        setattr(listing, field, value)
    listing.full_clean(exclude=["amenities"])
    listing.save()
    if amenity_names is not None:
        listing.amenities.set(_get_or_create_amenities(amenity_names))
    logger.info("Listing updated: %s", listing.public_id)
    return listing


def _get_or_create_amenities(names: list[str]) -> list[Amenity]:
    amenities = []
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        amenity, _created = Amenity.objects.get_or_create(
            slug=slugify(name), defaults={"name": name}
        )
        amenities.append(amenity)
    return amenities


@transaction.atomic
def add_listing_image(*, listing: Listing, image_file, is_main: bool = False) -> ListingImage:
    validate_image_upload(image_file)

    existing_count = listing.images.count()
    if existing_count >= MAX_IMAGES_PER_LISTING:
        raise DjangoValidationError(f"A listing may have at most {MAX_IMAGES_PER_LISTING} images.")

    if is_main or existing_count == 0:
        # Ensure only one main image at a time.
        listing.images.filter(is_main=True).update(is_main=False)
        is_main = True

    listing_image = ListingImage.objects.create(
        listing=listing,
        image=image_file,
        is_main=is_main,
        display_order=existing_count,
    )
    logger.info("Image added to listing %s", listing.public_id)
    return listing_image


@transaction.atomic
def delete_listing_image(*, listing_image: ListingImage) -> None:
    listing = listing_image.listing
    was_main = listing_image.is_main
    listing_image.image.delete(save=False)  # remove the file from storage, not just the DB row
    listing_image.delete()

    if was_main:
        next_image = listing.images.order_by("display_order").first()
        if next_image:
            next_image.is_main = True
            next_image.save(update_fields=["is_main"])
