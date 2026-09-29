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
