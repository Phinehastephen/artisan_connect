from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from artisans.models import Artisan
from services.models import Service

from .services import add_service_to_artisan, update_artisan_profile


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
                minimum_price=1000,
                maximum_price=5000,
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


class ArtisanProfileUpdateTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="artisan1",
            email="artisan@example.com",
            password="testpassword123",
            full_name="Original Name",
        )

        self.artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )

        # Four active services so tests can try "3 is fine, 4 is too many".
        self.services = []

        for number in range(1, 5):
            service = Service.objects.create(
                name=f"Service {number}",
                description=f"Test service {number}",
                minimum_price=1000,
                maximum_price=5000,
                is_active=True,
            )

            self.services.append(service)

    def test_artisan_can_update_own_fields(self):
        # Mixes fields that live on Artisan (business_name, phone_number,
        # default_location) with one that lives on the linked User
        # (full_name), since update_artisan_profile writes to both.
        # starting_price/maximum_price are intentionally not settable here:
        # they're derived from the artisan's assigned services (see
        # test_price_range_is_derived_from_assigned_services below).
        update_artisan_profile(
            self.artisan,
            business_name="Steve Electrical Services",
            phone_number="08011111111",
            default_location="Lagos",
            full_name="Steve Okonkwo",
        )

        # refresh_from_db() is required here: update_artisan_profile()
        # mutates the artisan/user objects in the database, but the local
        # Python objects in this test (self.artisan, self.artisan.user)
        # won't reflect that until we reload them.
        self.artisan.refresh_from_db()
        self.artisan.user.refresh_from_db()

        self.assertEqual(self.artisan.business_name, "Steve Electrical Services")
        self.assertEqual(self.artisan.phone_number, "08011111111")
        self.assertEqual(self.artisan.default_location, "Lagos")
        self.assertEqual(self.artisan.user.full_name, "Steve Okonkwo")

    def test_price_range_is_derived_from_assigned_services(self):
        # An artisan never sets their own price range: it's the min/max
        # across whichever services they're assigned, recalculated whenever
        # their service list changes.
        cheap_service, pricier_service = self.services[0], self.services[1]
        cheap_service.minimum_price = 1500
        cheap_service.maximum_price = 4000
        cheap_service.save()

        pricier_service.minimum_price = 3000
        pricier_service.maximum_price = 8000
        pricier_service.save()

        add_service_to_artisan(self.artisan, cheap_service)
        add_service_to_artisan(self.artisan, pricier_service)

        self.artisan.refresh_from_db()

        self.assertEqual(self.artisan.starting_price, 1500)
        self.assertEqual(self.artisan.maximum_price, 8000)