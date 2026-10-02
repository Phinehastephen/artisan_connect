from artisans.models import Artisan
from customers.models import Customer

import hashlib
import json
import logging
import threading
import time
from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count

from .models import SavedLocation

logger = logging.getLogger(__name__)


MAX_SAVED_LOCATIONS = 5


@transaction.atomic
def create_saved_location(
    customer,
    name,
    address,
    latitude,
    longitude,
):
    
    Customer.objects.select_for_update().get(pk=customer.pk)

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

    artisans = (
        Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .select_related("user")

        .annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        )
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


# openstreetmap 
GEOCODE_CACHE_TTL_SECONDS = 60 * 60 * 24
GEOCODE_MAX_RESULTS = 5
NOMINATIM_MIN_INTERVAL_SECONDS = 1.0

_nominatim_lock = threading.Lock()
_nominatim_last_request_at = 0.0


class GeocodingUnavailable(Exception):
    """Nominatim couldn't be reached or returned an unusable response."""


def _nominatim_get(path, params):
  
    global _nominatim_last_request_at

    params = {**params, "format": "jsonv2"}
    url = f"{settings.NOMINATIM_BASE_URL}/{path}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": settings.NOMINATIM_USER_AGENT,
            "Accept-Language": "en",
        },
    )

    with _nominatim_lock:
        wait = NOMINATIM_MIN_INTERVAL_SECONDS - (
            time.monotonic() - _nominatim_last_request_at
        )
        if wait > 0:
            time.sleep(wait)

        try:
            with urlopen(request, timeout=settings.NOMINATIM_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError) as error:
            logger.warning("Nominatim request failed: %s", error)
            raise GeocodingUnavailable(
                "The map service is unavailable right now. Please try again shortly."
            ) from error
        finally:
            _nominatim_last_request_at = time.monotonic()


def _format_place(place):
    return {
        "display_name": place["display_name"],
        "latitude": round(float(place["lat"]), 6),
        "longitude": round(float(place["lon"]), 6),
    }


def geocode_address(query):
    
    query = " ".join(query.split())
    cache_key = "geocode:" + hashlib.sha256(query.lower().encode()).hexdigest()

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {"q": query, "limit": GEOCODE_MAX_RESULTS}
    if settings.NOMINATIM_COUNTRY_CODES:
        params["countrycodes"] = settings.NOMINATIM_COUNTRY_CODES

    places = _nominatim_get("search", params)

    if not isinstance(places, list):
        raise GeocodingUnavailable(
            "The map service returned an unexpected response."
        )

    results = [_format_place(place) for place in places]
    cache.set(cache_key, results, GEOCODE_CACHE_TTL_SECONDS)

    return results


def reverse_geocode(latitude, longitude):
    
    
    latitude = round(float(latitude), 5)
    longitude = round(float(longitude), 5)
    cache_key = f"reverse-geocode:{latitude}:{longitude}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    place = _nominatim_get(
        "reverse",
        {"lat": latitude, "lon": longitude},
    )

    if not isinstance(place, dict):
        raise GeocodingUnavailable(
            "The map service returned an unexpected response."
        )

    result = {} if "error" in place else _format_place(place)
    cache.set(cache_key, result, GEOCODE_CACHE_TTL_SECONDS)

    return result or None
