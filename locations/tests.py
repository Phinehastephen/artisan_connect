from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from customers.models import Customer

from .services import create_saved_location


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