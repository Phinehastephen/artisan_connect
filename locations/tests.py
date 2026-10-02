import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.core.cache import cache
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from artisans.models import Artisan
from customers.models import Customer
from .services import (
    calculate_distance_km,
    create_saved_location,
    find_nearby_artisans,
    is_within_nearby_radius,
    resolve_search_coordinates,
    GeocodingUnavailable,
    geocode_address,
    reverse_geocode,
)
from .models import SavedLocation


class SavedLocationBusinessLogicTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="testpassword123",
        )

        self.customer = Customer.objects.create(
            user=user,
        )

    def _save_location(self, number):
        return create_saved_location(
            customer=self.customer,
            name=f"Location {number}",
            address=f"Test Address {number}",
            latitude=6.524400,
            longitude=3.379200,
        )

    def test_customer_can_save_five_locations(self):
        for number in range(1, 6):
            self._save_location(number)

        self.assertEqual(
            self.customer.saved_locations.count(),
            5,
        )

    def test_customer_cannot_save_sixth_location(self):
        for number in range(1, 6):
            self._save_location(number)

        with self.assertRaises(ValidationError):
            self._save_location(6)

        self.assertEqual(
            self.customer.saved_locations.count(),
            5,
        )


class DistanceCalculationTests(TestCase):

    def test_same_coordinates_return_zero_distance(self):
        distance = calculate_distance_km(
            6.524400,
            3.379200,
            6.524400,
            3.379200,
        )

        self.assertAlmostEqual(distance, 0, places=5)

    def test_known_coordinates_return_reasonable_distance(self):
        distance = calculate_distance_km(
            6.524400,
            3.379200,
            6.600000,
            3.350000,
        )

        self.assertAlmostEqual(distance, 8.95, delta=1.0)


class NearbyRadiusTests(TestCase):

    def test_location_within_10_km_is_nearby(self):
        self.assertTrue(
            is_within_nearby_radius(5.0)
        )

    def test_location_exactly_10_km_is_nearby(self):
        self.assertTrue(
            is_within_nearby_radius(10.0)
        )

    def test_location_beyond_10_km_is_not_nearby(self):
        self.assertFalse(
            is_within_nearby_radius(10.01)
        )


class NearbyArtisanTests(TestCase):

    def setUp(self):
        self.customer_latitude = 6.524400
        self.customer_longitude = 3.379200

        self.verified_artisan = self._create_artisan(
            "verified_artisan",
            Artisan.VerificationStatus.VERIFIED,
            latitude=6.530000,
            longitude=3.380000,
        )

        self.pending_artisan = self._create_artisan(
            "pending_artisan",
            Artisan.VerificationStatus.PENDING,
            latitude=6.530000,
            longitude=3.380000,
        )

        self.rejected_artisan = self._create_artisan(
            "rejected_artisan",
            Artisan.VerificationStatus.REJECTED,
            latitude=6.530000,
            longitude=3.380000,
        )

        self.far_artisan = self._create_artisan(
            "far_artisan",
            Artisan.VerificationStatus.VERIFIED,
            latitude=6.700000,
            longitude=3.500000,
        )

        self.nearby = [
            item["artisan"]
            for item in find_nearby_artisans(
                self.customer_latitude,
                self.customer_longitude,
            )
        ]

    def _create_artisan(self, username, verification_status, latitude, longitude):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
            role=User.Role.ARTISAN,
        )

        return Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status=verification_status,
            latitude=latitude,
            longitude=longitude,
        )

    def test_verified_nearby_artisan_is_returned(self):
        self.assertIn(self.verified_artisan, self.nearby)

    def test_pending_artisan_is_not_returned(self):
        self.assertNotIn(self.pending_artisan, self.nearby)

    def test_rejected_artisan_is_not_returned(self):
        self.assertNotIn(self.rejected_artisan, self.nearby)

    def test_far_artisan_is_not_returned(self):
        self.assertNotIn(self.far_artisan, self.nearby)


class SearchCoordinateResolutionTests(TestCase):

    def setUp(self):
        self.customer_user = User.objects.create_user(
            username="customer_a",
            email="customer_a@example.com",
            password="testpassword123",
            role=User.Role.CUSTOMER,
        )
        customer = Customer.objects.create(user=self.customer_user)

        self.saved_location = create_saved_location(
            customer=customer,
            name="Home",
            address="Home Address",
            latitude=6.524400,
            longitude=3.379200,
        )

        other_user = User.objects.create_user(
            username="customer_b",
            email="customer_b@example.com",
            password="testpassword123",
            role=User.Role.CUSTOMER,
        )
        other_customer = Customer.objects.create(user=other_user)

        self.other_location = create_saved_location(
            customer=other_customer,
            name="Other Home",
            address="Other Address",
            latitude=9.076500,
            longitude=7.398600,
        )

    def test_current_returns_supplied_coordinates(self):
        coordinates = resolve_search_coordinates(
            self.customer_user,
            "current",
            latitude=6.6,
            longitude=3.35,
        )

        self.assertEqual(coordinates, (6.6, 3.35))

    def test_saved_returns_own_saved_location_coordinates(self):
        latitude, longitude = resolve_search_coordinates(
            self.customer_user,
            "saved",
            location_id=self.saved_location.id,
        )

        self.assertEqual(latitude, self.saved_location.latitude)
        self.assertEqual(longitude, self.saved_location.longitude)

    def test_saved_cannot_use_another_customers_location(self):
        with self.assertRaises(SavedLocation.DoesNotExist):
            resolve_search_coordinates(
                self.customer_user,
                "saved",
                location_id=self.other_location.id,
            )

    def test_saved_is_rejected_for_non_customers(self):
        artisan_user = User.objects.create_user(
            username="artisan_x",
            email="artisan_x@example.com",
            password="testpassword123",
            role=User.Role.ARTISAN,
        )

        with self.assertRaises(ValidationError):
            resolve_search_coordinates(
                artisan_user,
                "saved",
                location_id=self.saved_location.id,
            )


def _nominatim_response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    return response


@patch("locations.services.NOMINATIM_MIN_INTERVAL_SECONDS", 0)
class GeocodingTests(TestCase):

    def setUp(self):
        cache.clear()

    @patch("locations.services.urlopen")
    def test_geocode_returns_candidate_places(self, mock_urlopen):
        mock_urlopen.return_value = _nominatim_response([
            {"display_name": "Yaba, Lagos, Nigeria", "lat": "6.5095442", "lon": "3.3710936"},
        ])

        results = geocode_address("Yaba, Lagos")

        self.assertEqual(
            results,
            [{"display_name": "Yaba, Lagos, Nigeria", "latitude": 6.509544, "longitude": 3.371094}],
        )

        request = mock_urlopen.call_args[0][0]
        self.assertIn("countrycodes=ng", request.full_url)
        self.assertIn("ArtisanConnect", request.get_header("User-agent"))

    @patch("locations.services.urlopen")
    def test_geocode_results_are_cached(self, mock_urlopen):
        mock_urlopen.return_value = _nominatim_response([])

        geocode_address("Nowhere Street")
        geocode_address("  nowhere   street ")

        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("locations.services.urlopen", side_effect=URLError("down"))
    def test_geocode_raises_when_service_unavailable(self, mock_urlopen):
        with self.assertRaises(GeocodingUnavailable):
            geocode_address("Yaba, Lagos")

    @patch("locations.services.urlopen")
    def test_reverse_geocode_returns_address(self, mock_urlopen):
        mock_urlopen.return_value = _nominatim_response(
            {"display_name": "Herbert Macaulay Way, Yaba", "lat": "6.5244", "lon": "3.3792"}
        )

        place = reverse_geocode(6.5244, 3.3792)

        self.assertEqual(place["display_name"], "Herbert Macaulay Way, Yaba")

    @patch("locations.services.urlopen")
    def test_reverse_geocode_with_no_address_returns_none_and_is_cached(self, mock_urlopen):
        mock_urlopen.return_value = _nominatim_response({"error": "Unable to geocode"})

        self.assertIsNone(reverse_geocode(0.0, 0.0))
        self.assertIsNone(reverse_geocode(0.0, 0.0))
        self.assertEqual(mock_urlopen.call_count, 1)


class NearbyArtisanMarkerTests(TestCase):

    def setUp(self):
        from services.models import Service

        self.artisan_user = User.objects.create_user(
            username="marker_artisan",
            email="marker_artisan@example.com",
            password="testpassword123",
            full_name="John Doe",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08000000099",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            business_name="John Plumbing",
            default_location="Yaba, Lagos",
            latitude=6.531234,
            longitude=3.381987,
            starting_price=1000,
            maximum_price=5000,
        )
        self.service = Service.objects.create(
            name="Plumbing",
            description="General plumbing services",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )

    def _markers(self):
        from .serializers import NearbyArtisanMarkerSerializer

        return NearbyArtisanMarkerSerializer(
            find_nearby_artisans(6.524400, 3.379200), many=True
        ).data

    def _add_review(self, number, rating):
        from bookings.models import Booking
        from reviews.models import Review

        user = User.objects.create_user(
            username=f"reviewer{number}",
            email=f"reviewer{number}@example.com",
            password="testpassword123",
        )
        customer = Customer.objects.create(user=user)
        booking = Booking.objects.create(
            customer=customer,
            artisan=self.artisan,
            service=self.service,
            status=Booking.Status.COMPLETED,
        )
        Review.objects.create(
            booking=booking,
            customer=customer,
            artisan=self.artisan,
            rating=rating,
        )

    def test_marker_contains_only_discovery_fields(self):
        marker = self._markers()[0]

        self.assertEqual(
            set(marker),
            {
                "id", "name", "is_verified", "distance_km", "location",
                "latitude", "longitude", "average_rating", "review_count",
                "starting_price", "maximum_price",
            },
        )
        self.assertEqual(marker["name"], "John Plumbing")
        self.assertTrue(marker["is_verified"])
        self.assertEqual(marker["location"], "Yaba, Lagos")

    def test_marker_coordinates_are_rounded(self):
        marker = self._markers()[0]

        self.assertEqual(marker["latitude"], 6.531)
        self.assertEqual(marker["longitude"], 3.382)

    def test_marker_name_falls_back_to_full_name(self):
        self.artisan.business_name = ""
        self.artisan.save(update_fields=["business_name"])

        self.assertEqual(self._markers()[0]["name"], "John Doe")

    def test_marker_rating_is_averaged(self):
        self.assertIsNone(self._markers()[0]["average_rating"])
        self.assertEqual(self._markers()[0]["review_count"], 0)

        self._add_review(1, 5)
        self._add_review(2, 4)

        marker = self._markers()[0]
        self.assertEqual(marker["average_rating"], 4.5)
        self.assertEqual(marker["review_count"], 2)
