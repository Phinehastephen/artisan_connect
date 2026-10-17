from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

from rest_framework.test import APIClient

from accounts.models import User
from artisans.models import Artisan, ServiceQualificationEvidence
from services.models import Service

from .services import (
    add_service_to_artisan,
    approve_artisan,
    reject_artisan,
    update_artisan_profile,
)


def make_qualification_evidence():
    return {
        "trade_certificate": [SimpleUploadedFile(
            "trade-certificate.pdf", b"%PDF-1.4\ncertificate content", content_type="application/pdf"
        )],
        "training_completion": [SimpleUploadedFile(
            "training.jpg", b"\xff\xd8\xff\xe0training evidence", content_type="image/jpeg"
        )],
    }


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

        self.assertEqual(self.artisan.business_name,
                         "Steve Electrical Services")
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
        update_artisan_profile(
            self.artisan, business_name="", profile_picture="")

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


class ServiceChangeRequestTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="svc_artisan",
            email="svc_artisan@example.com",
            password="testpassword123",
        )
        self.artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )

        self.service_a = Service.objects.create(
            name="Plumbing",
            minimum_price=2000,
            maximum_price=8000,
            is_active=True,
        )
        self.service_b = Service.objects.create(
            name="Electrical",
            minimum_price=2500,
            maximum_price=10000,
            is_active=True,
        )
        self.service_c = Service.objects.create(
            name="Painting",
            minimum_price=1800,
            maximum_price=6000,
            is_active=True,
        )
        self.service_d = Service.objects.create(
            name="Carpentry",
            minimum_price=2200,
            maximum_price=7000,
            is_active=True,
        )

        self.artisan.services.add(self.service_a, self.service_b)

    def tearDown(self):
        for evidence in ServiceQualificationEvidence.objects.all():
            evidence.file.delete(save=False)

    def test_service_change_must_replace_existing_service(self):
        from .services import create_service_change_request

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_a.id, self.service_b.id],
                qualification_evidence=make_qualification_evidence(),
                reason="I want to add another service to my profile.",
            )

    def test_service_change_cannot_exceed_three_services(self):
        from .services import create_service_change_request

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[
                    self.service_a.id,
                    self.service_b.id,
                    self.service_c.id,
                    self.service_d.id,
                ],
                qualification_evidence=make_qualification_evidence(),
                reason="I want to replace services but selected too many.",
            )

    def test_service_change_requires_two_evidence_categories(self):
        from .services import create_service_change_request

        evidence = make_qualification_evidence()
        evidence.pop("training_completion")
        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_a.id, self.service_c.id],
                qualification_evidence=evidence,
                reason="I want to replace my electrical service with painting work.",
            )

    def test_evidence_content_must_match_filename_extension(self):
        from .services import create_service_change_request

        evidence = make_qualification_evidence()
        evidence["trade_certificate"] = [SimpleUploadedFile(
            "trade-certificate.pdf", b"this is not a PDF", content_type="application/pdf"
        )]

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_a.id, self.service_c.id],
                qualification_evidence=evidence,
                reason="I want to replace my electrical service with painting work.",
            )

    def test_evidence_filename_cannot_contain_a_path(self):
        from .services import create_service_change_request

        evidence = make_qualification_evidence()
        evidence["trade_certificate"][0]._name = "../trade-certificate.pdf"

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_a.id, self.service_c.id],
                qualification_evidence=evidence,
                reason="I want to replace my electrical service with painting work.",
            )

    def test_private_evidence_storage_uses_configured_root(self):
        from pathlib import Path
        from django.conf import settings

        storage = ServiceQualificationEvidence._meta.get_field("file").storage
        expected_root = Path(settings.PRIVATE_UPLOAD_ROOT) / \
            "service_qualification_evidence"
        self.assertEqual(Path(storage.location), expected_root)

    def test_artisan_can_submit_pending_service_change_request(self):
        from .services import create_service_change_request

        request = create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.service_a.id, self.service_c.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I want to replace my electrical service with painting work.",
        )

        self.assertEqual(request.status, "PENDING")
        self.assertEqual(request.artisan, self.artisan)
        self.assertEqual(request.services.count(), 2)

    def test_artisan_cannot_submit_two_pending_requests(self):
        from .services import create_service_change_request

        create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.service_a.id, self.service_c.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I want to replace electrical work with painting.",
        )

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_b.id, self.service_d.id],
                qualification_evidence=make_qualification_evidence(),
                reason="I want to change my service mix again.",
            )

    def test_approving_change_request_updates_artisan_services(self):
        from .services import create_service_change_request, approve_service_change_request

        request = create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.service_a.id, self.service_c.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I want to replace electrical work with painting.",
        )

        approved = approve_service_change_request(request)

        self.artisan.refresh_from_db()
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(set(self.artisan.services.values_list("id", flat=True)), {
            self.service_a.id,
            self.service_c.id,
        })

    def test_approved_request_enforces_twelve_month_cooldown(self):
        from .services import create_service_change_request, approve_service_change_request

        request = create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.service_a.id, self.service_c.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I want to replace electrical work with painting.",
        )
        approve_service_change_request(request)

        with self.assertRaises(ValidationError):
            create_service_change_request(
                artisan=self.artisan,
                service_ids=[self.service_b.id, self.service_d.id],
                qualification_evidence=make_qualification_evidence(),
                reason="I want another service update too soon.",
            )


class ServiceChangeRequestApiAndEmailTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.service = Service.objects.create(
            name="Plumbing",
            minimum_price=2000,
            maximum_price=8000,
            is_active=True,
        )
        self.other_service = Service.objects.create(
            name="Electrical",
            minimum_price=2500,
            maximum_price=10000,
            is_active=True,
        )
        self.artisan_user = User.objects.create_user(
            username="requesting_artisan",
            email="requesting@example.com",
            password="testpassword123",
            full_name="Requesting Artisan",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08000000000",
            verification_status=Artisan.VerificationStatus.VERIFIED,
        )
        self.other_user = User.objects.create_user(
            username="other_artisan",
            email="other@example.com",
            password="testpassword123",
            full_name="Other Artisan",
            role=User.Role.ARTISAN,
        )
        self.other_artisan = Artisan.objects.create(
            user=self.other_user,
            phone_number="08000000001",
            verification_status=Artisan.VerificationStatus.VERIFIED,
        )
        self.artisan.services.add(self.service)
        self.other_artisan.services.add(self.other_service)
        self.admin = User.objects.create_user(
            username="service_admin",
            email="admin@example.com",
            password="testpassword123",
            full_name="Service Admin",
            role=User.Role.ADMIN,
        )
        self.url = "/api/v1/artisans/service-change-requests"
        self.request_data = {
            "services": [self.other_service.id],
            "reason": "I would like to focus on electrical work.",
        }

    def tearDown(self):
        for evidence in ServiceQualificationEvidence.objects.all():
            evidence.file.delete(save=False)

    def test_artisan_cannot_submit_a_request_for_another_artisan(self):
        self.client.force_authenticate(user=self.artisan_user)

        response = self.client.post(
            self.url,
            {**self.request_data, "artisan": self.other_artisan.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.other_artisan.service_change_requests.exists())
        self.assertFalse(self.artisan.service_change_requests.exists())

    def test_artisan_can_only_list_own_requests(self):
        from .services import create_service_change_request

        own_request = create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.other_service.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I would like to focus on electrical work.",
        )
        create_service_change_request(
            artisan=self.other_artisan,
            service_ids=[self.service.id],
            qualification_evidence=make_qualification_evidence(),
            reason="I would like to focus on plumbing work.",
        )
        self.client.force_authenticate(user=self.artisan_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"]
                         for item in response.data], [own_request.id])

    def test_multipart_request_requires_two_evidence_categories(self):
        self.client.force_authenticate(user=self.artisan_user)

        response = self.client.post(
            self.url,
            {
                "services": [self.other_service.id],
                "reason": "I want to replace plumbing with electrical work.",
                "trade_certificate": SimpleUploadedFile(
                    "certificate.pdf", b"%PDF-1.4\ncertificate", content_type="application/pdf"
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.artisan.service_change_requests.exists())

    def test_evidence_download_is_private_and_available_to_owner_and_admin(self):
        self.client.force_authenticate(user=self.artisan_user)
        with patch("artisans.services.send_mail"):
            with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        self.url,
                        {
                            "services": [self.other_service.id],
                            "reason": "I want to replace plumbing with electrical work.",
                            "trade_certificate": SimpleUploadedFile(
                                "certificate.pdf", b"%PDF-1.4\ncertificate", content_type="application/pdf"
                            ),
                            "training_completion": SimpleUploadedFile(
                                "training.jpg", b"\xff\xd8\xff\xe0training evidence", content_type="image/jpeg"
                            ),
                        },
                        format="multipart",
                    )

        self.assertEqual(response.status_code, 201, response.data)
        evidence_url = response.data["qualification_evidence"][0]["download_url"]

        self.client.force_authenticate(user=self.other_user)
        denied_response = self.client.get(evidence_url)
        self.assertEqual(denied_response.status_code, 404)

        self.client.force_authenticate(user=self.artisan_user)
        owner_response = self.client.get(evidence_url)
        self.assertEqual(owner_response.status_code, 200)
        for close_stream in owner_response._resource_closers:
            close_stream()

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get(evidence_url)
        self.assertEqual(admin_response.status_code, 200)
        for close_stream in admin_response._resource_closers:
            close_stream()

    def test_new_request_emails_all_active_admins(self):
        from .services import create_service_change_request

        inactive_admin = User.objects.create_user(
            username="inactive_service_admin",
            email="inactive-admin@example.com",
            password="testpassword123",
            full_name="Inactive Admin",
            role=User.Role.ADMIN,
            is_active=False,
        )
        with patch("artisans.services.send_mail") as mocked_send_mail:
            with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
                with self.captureOnCommitCallbacks(execute=True):
                    create_service_change_request(
                        artisan=self.artisan,
                        service_ids=[self.other_service.id],
                        qualification_evidence=make_qualification_evidence(),
                        reason="I would like to focus on electrical work.",
                    )

        mocked_send_mail.assert_called_once()
        recipients = mocked_send_mail.call_args.kwargs["recipient_list"]
        self.assertEqual(recipients, [self.admin.email])
        self.assertNotIn(inactive_admin.email, recipients)
        self.assertIn("needs review",
                      mocked_send_mail.call_args.kwargs["subject"])

    def test_approval_emails_the_requesting_artisan(self):
        from .services import approve_service_change_request, create_service_change_request

        with patch("artisans.services.send_mail") as mocked_send_mail:
            with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
                with self.captureOnCommitCallbacks(execute=True):
                    service_request = create_service_change_request(
                        artisan=self.artisan,
                        service_ids=[self.other_service.id],
                        qualification_evidence=make_qualification_evidence(),
                        reason="I would like to focus on electrical work.",
                    )
                mocked_send_mail.reset_mock()
                with self.captureOnCommitCallbacks(execute=True):
                    approve_service_change_request(service_request)

        mocked_send_mail.assert_called_once()
        self.assertEqual(
            mocked_send_mail.call_args.kwargs["recipient_list"],
            [self.artisan_user.email],
        )
        self.assertIn("approved", mocked_send_mail.call_args.kwargs["subject"])

    def test_rejection_emails_the_requesting_artisan(self):
        from .services import create_service_change_request, reject_service_change_request

        with patch("artisans.services.send_mail") as mocked_send_mail:
            with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
                with self.captureOnCommitCallbacks(execute=True):
                    service_request = create_service_change_request(
                        artisan=self.artisan,
                        service_ids=[self.other_service.id],
                        qualification_evidence=make_qualification_evidence(),
                        reason="I would like to focus on electrical work.",
                    )
                mocked_send_mail.reset_mock()
                with self.captureOnCommitCallbacks(execute=True):
                    reject_service_change_request(service_request)

        mocked_send_mail.assert_called_once()
        self.assertEqual(
            mocked_send_mail.call_args.kwargs["recipient_list"],
            [self.artisan_user.email],
        )
        self.assertIn("rejected", mocked_send_mail.call_args.kwargs["subject"])
