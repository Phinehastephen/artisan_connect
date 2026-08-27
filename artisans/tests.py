from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from artisans.models import Artisan
from services.models import Service

from .services import add_service_to_artisan


class ArtisanBusinessLogicTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="artisan1",
            email="artisan@example.com",
            password="testpassword123",
        )

        self.artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )

        self.services = []

        for number in range(1, 5):
            service = Service.objects.create(
                name=f"Service {number}",
                description=f"Test service {number}",
                is_active=True,
            )

            self.services.append(service)

    def test_artisan_can_have_three_services(self):
        for service in self.services[:3]:
            add_service_to_artisan(
                self.artisan,
                service,
            )

        self.assertEqual(
            self.artisan.services.count(),
            3,
        )

    def test_artisan_cannot_have_four_services(self):
        for service in self.services[:3]:
            add_service_to_artisan(
                self.artisan,
                service,
            )

        with self.assertRaises(ValidationError):
            add_service_to_artisan(
                self.artisan,
                self.services[3],
            )

        self.assertEqual(
            self.artisan.services.count(),
            3,
        )