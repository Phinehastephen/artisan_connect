from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import User
from artisans.models import Artisan
from services.models import Service

from .services import (
    add_service_to_artisan,
    approve_artisan,
    reject_artisan,
    update_artisan_profile,
)


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


class ArtisanIntegrityTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="integrity_artisan",
            email="integrity_artisan@example.com",
            password="testpassword123",
            full_name="Same Name",
        )
        self.artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
            business_name="Same Business",
        )

    def test_only_pending_artisans_can_be_approved_or_rejected(self):
        with self.assertRaises(ValidationError):
            approve_artisan(self.artisan)
        with self.assertRaises(ValidationError):
            reject_artisan(self.artisan)

        self.artisan.verification_status = "PENDING"
        self.artisan.save(update_fields=["verification_status"])
        approve_artisan(self.artisan)

        self.artisan.refresh_from_db()
        self.assertEqual(self.artisan.verification_status, "VERIFIED")

    def test_unchanged_values_do_not_start_a_cooldown(self):
        update_artisan_profile(
            self.artisan,
            full_name="Same Name",
            business_name="Same Business",
            phone_number="08099999999",
        )

        self.artisan.refresh_from_db()
        self.assertIsNone(self.artisan.user.full_name_updated_at)
        self.assertIsNone(self.artisan.business_name_updated_at)
        self.assertEqual(self.artisan.phone_number, "08099999999")

        # A real change is still allowed, and starts the cooldown.
        update_artisan_profile(self.artisan, full_name="New Name")
        self.artisan.refresh_from_db()
        self.assertIsNotNone(self.artisan.user.full_name_updated_at)

    def test_profile_coordinates_must_be_valid_and_together(self):
        from .serializers import ArtisanProfileUpdateSerializer

        for data in (
            {"latitude": 95, "longitude": 3.3},
            {"latitude": 6.5, "longitude": 200},
            {"latitude": 6.5},
        ):
            serializer = ArtisanProfileUpdateSerializer(
                self.artisan, data=data, partial=True
            )
            self.assertFalse(serializer.is_valid(), data)


class ArtisanAuditFixTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="audit_artisan",
            email="audit_artisan@example.com",
            password="testpassword123",
        )
        self.artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )

    def test_blank_and_empty_are_the_same_unchanged_value(self):
        update_artisan_profile(self.artisan, business_name="", profile_picture="")

        self.artisan.refresh_from_db()
        self.assertIsNone(self.artisan.business_name_updated_at)
        self.assertIsNone(self.artisan.user.profile_picture_updated_at)

    def test_coordinates_must_be_both_set_or_both_cleared(self):
        from .serializers import ArtisanProfileUpdateSerializer

        serializer = ArtisanProfileUpdateSerializer(
            self.artisan,
            data={"latitude": None, "longitude": "3.3"},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())

        serializer = ArtisanProfileUpdateSerializer(
            self.artisan,
            data={"latitude": None, "longitude": None},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_owner_profile_includes_coordinates(self):
        from .serializers import ArtisanProfileSerializer

        self.artisan.latitude = "6.524400"
        self.artisan.longitude = "3.379200"
        self.artisan.save()

        data = ArtisanProfileSerializer(self.artisan).data
        self.assertEqual(data["latitude"], "6.524400")
        self.assertEqual(data["longitude"], "3.379200")

    def test_inactive_services_do_not_count_toward_price_range(self):
        from artisans.services import recalculate_artisan_price_range

        cheap = Service.objects.create(
            name="Cheap", description="d", minimum_price=100,
            maximum_price=200, is_active=True,
        )
        pricey = Service.objects.create(
            name="Pricey", description="d", minimum_price=5000,
            maximum_price=9000, is_active=True,
        )
        self.artisan.services.add(cheap, pricey)
        recalculate_artisan_price_range(self.artisan)

        from services.services import update_service
        update_service(service=pricey, is_active=False)

        self.artisan.refresh_from_db()
        self.assertEqual(self.artisan.starting_price, 100)
        self.assertEqual(self.artisan.maximum_price, 200)
