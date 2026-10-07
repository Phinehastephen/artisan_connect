from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Min
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import Artisan


MAX_ARTISAN_SERVICES = 3


def _lock(artisan):
    Artisan.objects.select_for_update().filter(pk=artisan.pk).first()
    artisan.refresh_from_db()


@transaction.atomic
def add_service_to_artisan(artisan, service):
    _lock(artisan)

    if artisan.services.filter(id=service.id).exists():
        raise ValidationError(
            "This service is already assigned to the artisan."
        )

    if artisan.services.count() >= MAX_ARTISAN_SERVICES:
        raise ValidationError(
            "An artisan can offer a maximum of 3 services."
        )

    if not service.is_active:
        raise ValidationError(
            "This service is currently unavailable."
        )

    artisan.services.add(service)

    recalculate_artisan_price_range(artisan)

    return artisan


def recalculate_artisan_price_range(artisan):
    # Inactive services can't be booked, so they don't set the range.
    price_range = artisan.services.filter(is_active=True).aggregate(
        starting_price=Min("minimum_price"),
        maximum_price=Max("maximum_price"),
    )

    artisan.starting_price = price_range["starting_price"]
    artisan.maximum_price = price_range["maximum_price"]
    artisan.save(update_fields=["starting_price", "maximum_price"])


def _ensure_pending(artisan):
    if artisan.verification_status != Artisan.VerificationStatus.PENDING:
        raise ValidationError(
            "Only pending artisans can be approved or rejected."
        )


@transaction.atomic
def approve_artisan(artisan):
    # Locked so two admins acting at the same moment can't both decide.
    _lock(artisan)
    _ensure_pending(artisan)

    artisan.verification_status = Artisan.VerificationStatus.VERIFIED
    artisan.save(update_fields=["verification_status"])

    return artisan


@transaction.atomic
def reject_artisan(artisan):
    _lock(artisan)
    _ensure_pending(artisan)

    artisan.verification_status = Artisan.VerificationStatus.REJECTED
    artisan.save(update_fields=["verification_status"])

    return artisan


@transaction.atomic
def update_artisan_profile(artisan, **fields):

    if artisan.verification_status != Artisan.VerificationStatus.VERIFIED:
        raise ValidationError(
            "Only verified artisans can modify their profile."
        )

    user = artisan.user
    now = timezone.now()

    # Apps often send the whole form; an unchanged value mustn't start (or
    # trip) a 6-month cooldown.
    current = {
        "full_name": user.full_name,
        "profile_picture": user.profile_picture,
        "business_name": artisan.business_name,
    }
    fields = {
        name: value
        for name, value in fields.items()
        if not (name in current and (value or None) == (current[name] or None))
    }

    # Full name
    if "full_name" in fields:
        if (
            user.full_name_updated_at is not None
            and now < user.full_name_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Full name can only be changed once every 6 months."
            )

        user.full_name = fields["full_name"]
        user.full_name_updated_at = now

    # Profile picture
    if "profile_picture" in fields:
        if (
            user.profile_picture_updated_at is not None
            and now < user.profile_picture_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Profile picture can only be changed once every 6 months."
            )

        user.profile_picture = fields["profile_picture"]
        user.profile_picture_updated_at = now

    # Business name
    if "business_name" in fields:
        if (
            artisan.business_name_updated_at is not None
            and now < artisan.business_name_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Business name can only be changed once every 6 months."
            )

        artisan.business_name = fields["business_name"]
        artisan.business_name_updated_at = now

    # Operational fields
    if "phone_number" in fields:
        artisan.phone_number = fields["phone_number"]

    if "default_location" in fields:
        artisan.default_location = fields["default_location"]

    if "latitude" in fields:
        artisan.latitude = fields["latitude"]

    if "longitude" in fields:
        artisan.longitude = fields["longitude"]

    # Save User changes
    user_fields_to_update = []

    if "full_name" in fields:
        user_fields_to_update.extend([
            "full_name",
            "full_name_updated_at",
        ])

    if "profile_picture" in fields:
        user_fields_to_update.extend([
            "profile_picture",
            "profile_picture_updated_at",
        ])

    if user_fields_to_update:
        user.save(update_fields=user_fields_to_update)

    # Save Artisan changes
    artisan_fields_to_update = []

    if "business_name" in fields:
        artisan_fields_to_update.extend([
            "business_name",
            "business_name_updated_at",
        ])

    if "phone_number" in fields:
        artisan_fields_to_update.append("phone_number")

    if "default_location" in fields:
        artisan_fields_to_update.append("default_location")

    if "latitude" in fields:
        artisan_fields_to_update.append("latitude")

    if "longitude" in fields:
        artisan_fields_to_update.append("longitude")

    if artisan_fields_to_update:
        artisan.save(update_fields=artisan_fields_to_update)

    return artisan