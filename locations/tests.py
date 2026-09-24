from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from customers.models import Customer

from .services import (
    calculate_distance_km,
    create_saved_location,
    is_within_nearby_radius,
)


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

    def test_customer_can_save_five_locations(self):
        for number in range(1, 6):
            create_saved_location(
                customer=self.customer,
                name=f"Location {number}",
                address=f"Test Address {number}",
                latitude=6.524400,
                longitude=3.379200,
            )

        self.assertEqual(
            self.customer.saved_locations.count(),
            5,
        )

    def test_customer_cannot_save_sixth_location(self):
        for number in range(1, 6):
            create_saved_location(
                customer=self.customer,
                name=f"Location {number}",
                address=f"Test Address {number}",
                latitude=6.524400,
                longitude=3.379200,
            )

        with self.assertRaises(ValidationError):
            create_saved_location(
                customer=self.customer,
                name="Location 6",
                address="Sixth Address",
                latitude=6.524400,
                longitude=3.379200,
            )

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

    def test_distance_is_returned_in_kilometers(self):
        distance = calculate_distance_km(
            6.524400,
            3.379200,
            6.600000,
            3.350000,
        )

        self.assertGreater(distance, 0)

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