from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2

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

    saved_location = SavedLocation(
        customer=customer,
        name=name,
        address=address,
        latitude=Decimal(str(latitude)),
        longitude=Decimal(str(longitude)),
    )

    saved_location.full_clean()
    saved_location.save()

    return saved_location


# Haversine formula to calculate distance between two geographic coordinates
def calculate_distance_km(
    latitude1,
    longitude1,
    latitude2,
    longitude2,
):

    earth_radius_km = 6371.0

    lat1 = radians(float(latitude1))
    lon1 = radians(float(longitude1))
    lat2 = radians(float(latitude2))
    lon2 = radians(float(longitude2))

    delta_latitude = lat2 - lat1
    delta_longitude = lon2 - lon1

    a = (
        sin(delta_latitude / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_longitude / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c

NEARBY_RADIUS_KM = 10


def is_within_nearby_radius(distance_km):
   
    return distance_km <= NEARBY_RADIUS_KM