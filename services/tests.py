from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from artisans.models import Artisan
from artisans.services import recalculate_artisan_price_range
from .models import Service, ServiceScopeOption, ServiceScopeQuestion
from .services import update_service


class ServicePriceRangeTests(TestCase):

    def test_changing_service_prices_updates_artisan_ranges(self):
        service = Service.objects.create(
            name="Plumbing Price Range Test",
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


class ServiceScopeApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(
            username="scope_customer",
            email="scope_customer@example.com",
            password="scope-test-password-2026",
            role=User.Role.CUSTOMER,
        )
        self.client.force_authenticate(user=user)
        self.service = Service.objects.create(
            name="Scope Test Service",
            minimum_price=15000,
            maximum_price=700000,
            is_active=True,
        )
        self.question = ServiceScopeQuestion.objects.create(
            service=self.service,
            key="occasion",
            label="Occasion",
            position=0,
        )
        ServiceScopeOption.objects.create(
            question=self.question,
            value="birthday",
            label="Birthday",
            position=0,
        )
        ServiceScopeOption.objects.create(
            question=self.question,
            value="inactive",
            label="Inactive option",
            position=1,
            is_active=False,
        )

    def test_scope_endpoint_returns_active_questions_and_options(self):
        response = self.client.get(
            f"/api/v1/services/{self.service.id}/scope"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["label"], "Occasion")
        self.assertEqual(
            [option["label"] for option in response.data[0]["options"]],
            ["Birthday"],
        )

    def test_v1_service_catalog_has_scope_questions(self):
        service_names = [
            "AC & Refrigeration",
            "Auto Repair",
            "Barber",
            "Cake Making",
            "Carpentry",
            "Cleaning",
            "Electrical",
            "Generator Repair",
            "Hair Stylist",
            "Makeup artist (MUA)",
            "Masonry",
            "Painting",
            "Plumbing",
            "Tailoring",
        ]
        services = Service.objects.filter(
            name__in=service_names,
            is_active=True,
        )

        self.assertSetEqual(
            set(services.values_list("name", flat=True)),
            set(service_names),
        )
        for service in services:
            with self.subTest(service=service.name):
                self.assertTrue(
                    service.scope_questions.filter(is_active=True).exists()
                )
