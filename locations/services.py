from django.core.exceptions import ValidationError
from django.db import transaction

from .models import SavedLocation


MAX_SAVED_LOCATIONS = 5


@transaction.atomic
def create_saved_location(
    customer,
    name,
    address,
    latitude,
    longitude,
):
    if customer.saved_locations.count() >= MAX_SAVED_LOCATIONS:
        raise ValidationError(
            "A customer can save a maximum of 5 locations."
        )

    return SavedLocation.objects.create(
        customer=customer,
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
    )