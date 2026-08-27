from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from artisans.models import Artisan
from customers.models import Customer
from services.models import Service

from .models import Booking
from .services import (
    create_booking,
    accept_booking,
    start_booking,
    complete_booking,
    finalize_booking,
)


class BookingBusinessLogicTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="testpassword123",
        )

        self.customer = Customer.objects.create(
            user=self.user,
        )

        artisan_user = User.objects.create_user(
            username="artisan1",
            email="artisan@example.com",
            password="testpassword123",
        )

        self.artisan = Artisan.objects.create(
            user=artisan_user,
            phone_number="08000000000",
            verification_status="VERIFIED",
        )

        self.service = Service.objects.create(
            name="Plumbing",
            description="General plumbing services",
            is_active=True,
        )

        self.artisan.services.add(self.service)

    def test_verified_artisan_can_receive_booking(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

        self.assertEqual(
            booking.customer,
            self.customer,
        )

        self.assertEqual(
            booking.artisan,
            self.artisan,
        )

        self.assertEqual(
            booking.service,
            self.service,
        )

    def test_unverified_artisan_cannot_receive_booking(self):
        self.artisan.verification_status = "PENDING"
        self.artisan.save()

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                artisan=self.artisan,
                service=self.service,
                job_address="Test Address",
                job_latitude=6.524400,
                job_longitude=3.379200,
            )

    def test_artisan_cannot_receive_unoffered_service(self):
        electrical = Service.objects.create(
            name="Electrical",
            description="Electrical services",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                artisan=self.artisan,
                service=electrical,
                job_address="Test Address",
                job_latitude=6.524400,
                job_longitude=3.379200,
            )

    def test_booking_lifecycle(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

        booking = accept_booking(booking)

        self.assertEqual(
            booking.status,
            Booking.Status.ACCEPTED,
        )

        self.assertIsNotNone(
            booking.accepted_at,
        )

        booking = start_booking(booking)

        self.assertEqual(
            booking.status,
            Booking.Status.IN_PROGRESS,
        )

        booking = complete_booking(booking)

        self.assertEqual(
            booking.status,
            Booking.Status.COMPLETED,
        )

        self.assertIsNotNone(
            booking.completed_at,
        )

    def test_booking_cannot_skip_status(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        with self.assertRaises(ValidationError):
            complete_booking(booking)
            
    def test_finalizing_booking_clears_job_location(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street, Lagos",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        booking.status = Booking.Status.COMPLETED
        booking.completed_at = timezone.now()
        booking.save(update_fields=["status", "completed_at"])

        finalize_booking(booking)

        booking.refresh_from_db()

        self.assertEqual(
            booking.status,
            Booking.Status.FINALIZED,
        )

        self.assertIsNotNone(
            booking.finalized_at,
        )

        self.assertIsNone(
            booking.job_address,
        )

        self.assertIsNone(
            booking.job_latitude,
        )

        self.assertIsNone(
            booking.job_longitude,
        )
        
    def test_incomplete_booking_cannot_be_finalized(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street, Lagos",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        with self.assertRaises(ValidationError):
            finalize_booking(booking)