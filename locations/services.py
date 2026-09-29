from artisans.models import Artisan

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

def resolve_search_coordinates(
    user,
    location_type,
    latitude=None,
    longitude=None,
    location_id=None,
):
    """
    Returns the (latitude, longitude) to search around.

    For "saved", the lookup is scoped to the requesting customer's own
    saved locations, so another customer's location_id raises
    SavedLocation.DoesNotExist (a 404) instead of revealing where it is.
    """
    if location_type != "saved":
        return latitude, longitude

    if user.role != user.Role.CUSTOMER:
        raise ValidationError(
            "Only customers can search from a saved location."
        )

    saved_location = SavedLocation.objects.get(
        pk=location_id,
        customer=user.customer_profile,
    )

    return saved_location.latitude, saved_location.longitude


# find nearby artisans within the configured nearby radius of the supplied coordinates
def find_nearby_artisans(latitude, longitude):

    nearby_artisans = []

    artisans = Artisan.objects.filter(
        verification_status=Artisan.VerificationStatus.VERIFIED,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    for artisan in artisans:
        distance_km = calculate_distance_km(
            latitude,
            longitude,
            artisan.latitude,
            artisan.longitude,
        )

        if is_within_nearby_radius(distance_km):
            nearby_artisans.append({
                "artisan": artisan,
                "distance_km": round(distance_km, 2),
            })

    nearby_artisans.sort(
        key=lambda item: item["distance_km"]
    )

    return nearby_artisans