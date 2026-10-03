from django.core.exceptions import ValidationError
from django.test import TestCase
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
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
    reject_booking,
    cancel_booking,
    confirm_completion,
    send_due_confirmation_reminders,
    auto_finalize_overdue_bookings,
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
            minimum_price=1000,
            maximum_price=5000,
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
            minimum_price=1000,
            maximum_price=5000,
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

    def test_pending_booking_can_be_rejected(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        booking = reject_booking(booking)

        self.assertEqual(
            booking.status,
            Booking.Status.CANCELLED,
        )

    def test_accepted_booking_cannot_be_rejected(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        booking = accept_booking(booking)

        with self.assertRaises(ValidationError):
            reject_booking(booking)

    def test_accepted_booking_can_be_cancelled(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        booking = accept_booking(booking)
        booking = cancel_booking(booking)

        self.assertEqual(
            booking.status,
            Booking.Status.CANCELLED,
        )

    def test_pending_booking_can_be_cancelled(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        booking = cancel_booking(booking)

        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_in_progress_booking_cannot_be_cancelled(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )
        accept_booking(booking)
        start_booking(booking)

        with self.assertRaises(ValidationError):
            cancel_booking(booking)

    def test_inactive_service_cannot_be_booked(self):
        self.service.is_active = False
        self.service.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            create_booking(
                customer=self.customer,
                artisan=self.artisan,
                service=self.service,
                job_address="Test Address",
                job_latitude=6.524400,
                job_longitude=3.379200,
            )

class BookingPrivacyTests(TestCase):
    """Contact and location details must not let the customer and artisan
    reach each other outside the app."""

    def setUp(self):
        self.customer_user = User.objects.create_user(
            username="privacy_customer",
            email="privacy_customer@example.com",
            password="testpassword123",
            role=User.Role.CUSTOMER,
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            phone_number="08011111111",
            default_location="12 Home Street",
        )

        self.artisan_user = User.objects.create_user(
            username="privacy_artisan",
            email="privacy_artisan@example.com",
            password="testpassword123",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08022222222",
            verification_status="VERIFIED",
        )

        self.admin_user = User.objects.create_user(
            username="privacy_admin",
            email="privacy_admin@example.com",
            password="testpassword123",
            role=User.Role.ADMIN,
        )

        self.service = Service.objects.create(
            name="Plumbing",
            description="General plumbing services",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.artisan.services.add(self.service)

        self.booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street, Lagos",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

    def _serialize_for(self, user):
        from rest_framework.test import APIRequestFactory
        from .serializers import BookingSerializer

        request = APIRequestFactory().get("/")
        request.user = user

        return BookingSerializer(
            self.booking, context={"request": request}
        ).data

    def test_artisan_cannot_see_job_location_while_pending(self):
        data = self._serialize_for(self.artisan_user)

        self.assertIsNone(data["job_address"])
        self.assertIsNone(data["job_latitude"])
        self.assertIsNone(data["job_longitude"])

    def test_artisan_sees_job_location_once_accepted_and_in_progress(self):
        accept_booking(self.booking)
        self.assertEqual(
            self._serialize_for(self.artisan_user)["job_address"],
            "12 Test Street, Lagos",
        )

        start_booking(self.booking)
        self.assertEqual(
            self._serialize_for(self.artisan_user)["job_address"],
            "12 Test Street, Lagos",
        )

    def test_artisan_cannot_see_job_location_after_completion(self):
        accept_booking(self.booking)
        start_booking(self.booking)
        complete_booking(self.booking)

        self.assertIsNone(
            self._serialize_for(self.artisan_user)["job_address"]
        )

    def test_customer_and_admin_always_see_job_location(self):
        self.assertEqual(
            self._serialize_for(self.customer_user)["job_address"],
            "12 Test Street, Lagos",
        )
        self.assertEqual(
            self._serialize_for(self.admin_user)["job_address"],
            "12 Test Street, Lagos",
        )

    def test_no_request_context_hides_job_location(self):
        from .serializers import BookingSerializer

        self.assertIsNone(BookingSerializer(self.booking).data["job_address"])

    def test_counterparty_details_have_no_phone_email_or_home(self):
        data = self._serialize_for(self.customer_user)

        for detail in (data["customer_detail"], data["artisan_detail"]):
            self.assertNotIn("phone_number", detail)
            self.assertNotIn("email", detail["user"])

        self.assertNotIn("default_location", data["customer_detail"])

    def test_rejecting_booking_clears_job_location(self):
        reject_booking(self.booking)
        self.booking.refresh_from_db()

        self.assertIsNone(self.booking.job_address)
        self.assertIsNone(self.booking.job_latitude)
        self.assertIsNone(self.booking.job_longitude)

    def test_cancelling_booking_clears_job_location(self):
        accept_booking(self.booking)
        cancel_booking(self.booking)
        self.booking.refresh_from_db()

        self.assertIsNone(self.booking.job_address)
        self.assertIsNone(self.booking.job_latitude)
        self.assertIsNone(self.booking.job_longitude)

    def test_review_booking_summary_has_no_job_location(self):
        from .serializers import BookingSummarySerializer

        data = BookingSummarySerializer(self.booking).data

        for field in ("job_address", "job_latitude", "job_longitude"):
            self.assertNotIn(field, data)


class CompletionConfirmationTests(TestCase):

    def setUp(self):
        customer_user = User.objects.create_user(
            username="confirm_customer",
            email="confirm_customer@example.com",
            password="testpassword123",
        )
        self.customer = Customer.objects.create(user=customer_user)

        artisan_user = User.objects.create_user(
            username="confirm_artisan",
            email="confirm_artisan@example.com",
            password="testpassword123",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=artisan_user,
            phone_number="08000000000",
            verification_status="VERIFIED",
            business_name="Joe Plumbing",
        )
        self.service = Service.objects.create(
            name="Plumbing",
            description="General plumbing services",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.artisan.services.add(self.service)

        self.booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )
        accept_booking(self.booking)
        start_booking(self.booking)
        complete_booking(self.booking)

    def _after(self, hours):
        return self.booking.completed_at + timedelta(hours=hours)

    def test_customer_confirmation_finalizes_booking(self):
        confirm_completion(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, Booking.Status.FINALIZED)
        self.assertEqual(
            self.booking.finalization_method,
            Booking.FinalizationMethod.CUSTOMER_CONFIRMED,
        )
        self.assertIsNone(self.booking.job_address)

    def test_cannot_confirm_before_artisan_completes(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        with self.assertRaises(ValidationError):
            confirm_completion(booking)

    def test_reminders_follow_schedule_and_stop_at_three(self):
        self.assertEqual(send_due_confirmation_reminders(self._after(23)), 0)
        self.assertEqual(send_due_confirmation_reminders(self._after(24)), 1)
        self.assertEqual(send_due_confirmation_reminders(self._after(30)), 0)
        self.assertEqual(send_due_confirmation_reminders(self._after(48)), 1)
        self.assertEqual(send_due_confirmation_reminders(self._after(66)), 1)
        self.assertEqual(send_due_confirmation_reminders(self._after(70)), 0)

        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[0].to, ["confirm_customer@example.com"])
        self.assertIn("Joe Plumbing", mail.outbox[0].body)
        self.assertIn("final reminder", mail.outbox[2].body)

    def test_no_reminder_once_confirmed(self):
        confirm_completion(self.booking)

        self.assertEqual(send_due_confirmation_reminders(self._after(25)), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_failed_reminder_is_retried(self):
        with patch("bookings.services.send_mail", side_effect=Exception("SMTP down")):
            self.assertEqual(send_due_confirmation_reminders(self._after(24)), 0)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.confirmation_reminders_sent, 0)
        self.assertEqual(send_due_confirmation_reminders(self._after(25)), 1)

    def test_auto_finalizes_after_three_days(self):
        self.assertEqual(auto_finalize_overdue_bookings(self._after(71)), 0)
        self.assertEqual(auto_finalize_overdue_bookings(self._after(72)), 1)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.FINALIZED)
        self.assertEqual(
            self.booking.finalization_method,
            Booking.FinalizationMethod.AUTO,
        )
        self.assertIsNone(self.booking.job_address)

    def test_finalized_booking_can_still_be_reviewed(self):
        from reviews.services import create_review

        confirm_completion(self.booking)

        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=5,
        )
        self.assertEqual(review.booking, self.booking)
