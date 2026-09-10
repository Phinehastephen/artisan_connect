from django.test import TestCase

from artisans.models import Artisan
from customers.models import Customer
from services.models import Service

from .models import User
from .services import register_customer, register_artisan


class AccountsBusinessLogicTests(TestCase):

    def setUp(self):
        self.services = []

        for number in range(1, 4):
            service = Service.objects.create(
                name=f"Service {number}",
                description=f"Test service {number}",
                is_active=True,
            )

            self.services.append(service)

    def test_register_customer_creates_user_and_profile(self):
        user = register_customer(
            {
                "username": "customer1",
                "email": "customer@example.com",
                "full_name": "Test Customer",
                "password": "testpassword123",
                "phone_number": "08000000000",
            }
        )

        self.assertEqual(
            user.role,
            User.Role.CUSTOMER,
        )

        self.assertTrue(
            user.check_password("testpassword123"),
        )

        customer = Customer.objects.get(user=user)

        self.assertEqual(
            customer.phone_number,
            "08000000000",
        )

    def test_register_artisan_creates_user_and_profile_with_services(self):
        user = register_artisan(
            {
                "username": "artisan1",
                "email": "artisan@example.com",
                "full_name": "Test Artisan",
                "password": "testpassword123",
                "phone_number": "08000000000",
                "services": self.services[:2],
            }
        )

        self.assertEqual(
            user.role,
            User.Role.ARTISAN,
        )

        self.assertTrue(
            user.check_password("testpassword123"),
        )

        artisan = Artisan.objects.get(user=user)

        self.assertEqual(
            artisan.phone_number,
            "08000000000",
        )

        self.assertEqual(
            artisan.services.count(),
            2,
        )

    def test_registered_artisan_starts_as_pending_verification(self):
        user = register_artisan(
            {
                "username": "artisan2",
                "email": "artisan2@example.com",
                "full_name": "Test Artisan",
                "password": "testpassword123",
                "phone_number": "08000000000",
                "services": self.services[:1],
            }
        )

        artisan = Artisan.objects.get(user=user)

        self.assertEqual(
            artisan.verification_status,
            Artisan.VerificationStatus.PENDING,
        )
