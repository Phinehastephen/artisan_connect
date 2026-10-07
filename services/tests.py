from django.test import TestCase

from accounts.models import User
from artisans.models import Artisan
from artisans.services import recalculate_artisan_price_range
from .models import Service
from .services import update_service


class ServicePriceRangeTests(TestCase):

    def test_changing_service_prices_updates_artisan_ranges(self):
        service = Service.objects.create(
            name="Plumbing",
            description="General plumbing services",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        user = User.objects.create_user(
            username="plumber",
            email="plumber@example.com",
            password="testpassword123",
        )
        artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )
        artisan.services.add(service)
        recalculate_artisan_price_range(artisan)

        update_service(service=service, minimum_price=1500, maximum_price=9000)

        artisan.refresh_from_db()
        self.assertEqual(artisan.starting_price, 1500)
        self.assertEqual(artisan.maximum_price, 9000)
