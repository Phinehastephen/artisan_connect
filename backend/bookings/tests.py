from django.core.exceptions import ValidationError
from django.test import TestCase
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from artisans.models import Artisan
from customers.models import Customer
from services.models import Service
from services.models import ServiceScopeOption, ServiceScopeQuestion

from .models import Booking
from .serializers import BookingCreateSerializer
from .services import (
    create_booking,
    accept_booking,
    mark_booking_on_the_way,
    start_booking,
    complete_booking,
    finalize_booking,
    reject_booking,
    cancel_booking,
    confirm_completion,
    dispute_completion,
    reopen_booking,
    send_due_confirmation_reminders,
    auto_finalize_overdue_bookings,
)


class BookingEventEmailTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.customer_user = User.objects.create_user(
            username="email_customer",
            email="email_customer@example.com",
            password="email-test-password",
            full_name="Email Customer",
            role=User.Role.CUSTOMER,
        )
        self.customer = Customer.objects.create(user=self.customer_user)
        self.artisan_user = User.objects.create_user(
            username="email_artisan",
            email="email_artisan@example.com",
            password="email-test-password",
            full_name="Email Artisan",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08000000001",
            verification_status="VERIFIED",
        )
        self.service = Service.objects.create(
            name="Email Test Plumbing",
            description="Plumbing services",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.artisan.services.add(self.service)

    def _run_after_commit(self, callback):
        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with self.captureOnCommitCallbacks(execute=True):
                return callback()

    def _create_booking(self):
        return create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Private job address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

    def test_key_booking_events_email_the_correct_party(self):
        booking = self._run_after_commit(self._create_booking)
        self.assertEqual(mail.outbox[-1].to, [self.artisan_user.email])
        self.assertIn("New booking request", mail.outbox[-1].subject)
        self.assertNotIn("Private job address", mail.outbox[-1].body)

        self._run_after_commit(lambda: accept_booking(booking))
        self.assertEqual(mail.outbox[-1].to, [self.customer_user.email])
        self.assertIn("accepted", mail.outbox[-1].body)

        self._run_after_commit(lambda: mark_booking_on_the_way(booking))
        self.assertEqual(mail.outbox[-1].to, [self.customer_user.email])
        self.assertIn("on the way", mail.outbox[-1].body)

        self._run_after_commit(lambda: start_booking(booking))
        self.assertEqual(len(mail.outbox), 3)

        self._run_after_commit(lambda: complete_booking(booking))
        self.assertEqual(mail.outbox[-1].to, [self.customer_user.email])
        self.assertIn("confirm the work", mail.outbox[-1].body)
        self.assertEqual(len(mail.outbox), 4)

    def test_decline_and_customer_cancellation_email_the_other_party(self):
        booking = self._run_after_commit(self._create_booking)
        mail.outbox = []

        self._run_after_commit(lambda: reject_booking(booking))
        self.assertEqual(mail.outbox[-1].to, [self.customer_user.email])
        self.assertIn("declined", mail.outbox[-1].body)

        booking = self._run_after_commit(self._create_booking)
        mail.outbox = []
        self._run_after_commit(lambda: cancel_booking(booking))
        self.assertEqual(mail.outbox[-1].to, [self.artisan_user.email])
        self.assertIn("cancelled", mail.outbox[-1].body)

    def test_email_failure_does_not_prevent_booking_creation(self):
        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with patch("bookings.services.send_mail", side_effect=Exception("SMTP down")):
                with self.captureOnCommitCallbacks(execute=True):
                    booking = self._create_booking()

        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertTrue(Booking.objects.filter(pk=booking.pk).exists())


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

        mark_booking_on_the_way(booking)
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
        mark_booking_on_the_way(booking)
        start_booking(booking)

        with self.assertRaises(ValidationError):
            cancel_booking(booking)

    def test_artisan_must_mark_on_the_way_before_starting(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )
        accept_booking(booking)

        with self.assertRaisesMessage(
            ValidationError,
            "Mark yourself on the way before starting the job.",
        ):
            start_booking(booking)

    def test_customer_cannot_cancel_after_artisan_marks_on_the_way(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )
        accept_booking(booking)
        mark_booking_on_the_way(booking)

        with self.assertRaisesMessage(
            ValidationError,
            "This booking can no longer be cancelled because the artisan is on the way.",
        ):
            cancel_booking(booking)

    def test_on_the_way_action_updates_customer_visible_workflow(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )
        accept_booking(booking)
        self.artisan.user.role = User.Role.ARTISAN
        self.artisan.user.save(update_fields=["role"])
        client = APIClient()
        client.force_authenticate(user=self.artisan.user)

        response = client.post(
            f"/api/v1/bookings/status/{booking.id}/on-the-way"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["workflow_status"], "ON_THE_WAY")
        self.assertIsNotNone(response.data["artisan_on_the_way_at"])

        client.force_authenticate(user=self.user)
        cancel_response = client.post(
            f"/api/v1/bookings/status/{booking.id}/cancel"
        )
        self.assertEqual(cancel_response.status_code, 400)

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

    def test_booking_scope_requires_and_snapshots_valid_answers(self):
        question = ServiceScopeQuestion.objects.create(
            service=self.service,
            key="task",
            label="Task",
            position=0,
        )
        option = ServiceScopeOption.objects.create(
            question=question,
            value="leak_repair",
            label="Leak repair",
            position=0,
        )
        data = {
            "artisan": self.artisan.id,
            "service": self.service.id,
            "job_location_type": "current",
            "job_latitude": "6.524400",
            "job_longitude": "3.379200",
            "scope_answers": [
                {"question": question.id, "option": option.id},
            ],
        }

        serializer = BookingCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["_scope_snapshot"],
            [{
                "key": "task",
                "question": "Task",
                "value": "leak_repair",
                "answer": "Leak repair",
            }],
        )
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
            scope_answers=serializer.validated_data["_scope_snapshot"],
        )
        self.assertEqual(booking.scope.answers[0]["answer"], "Leak repair")

        missing_answer = BookingCreateSerializer(
            data={**data, "scope_answers": []},
        )
        self.assertFalse(missing_answer.is_valid())
        self.assertIn("scope_answers", missing_answer.errors)


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
        mark_booking_on_the_way(self.booking)
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
        mark_booking_on_the_way(self.booking)
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
        mark_booking_on_the_way(self.booking)
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
            self.assertEqual(
                send_due_confirmation_reminders(self._after(24)), 0)

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

    REASON = "The tap is still leaking after the repair."

    def test_customer_can_dispute_with_a_reason(self):
        dispute_completion(self.booking, self.REASON)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, Booking.Status.DISPUTED)
        self.assertEqual(self.booking.dispute_reason, self.REASON)
        self.assertIsNotNone(self.booking.disputed_at)

    def test_dispute_needs_a_proper_reason(self):
        for reason in (None, "", "   bad job        ", "x" * 19):
            with self.assertRaises(ValidationError):
                dispute_completion(self.booking, reason)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_cannot_dispute_before_artisan_completes(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="12 Test Street",
            job_latitude=6.524400,
            job_longitude=3.379200,
        )

        with self.assertRaises(ValidationError):
            dispute_completion(booking, self.REASON)

    def test_dispute_stops_reminders_and_auto_finalize(self):
        dispute_completion(self.booking, self.REASON)

        self.assertEqual(send_due_confirmation_reminders(self._after(30)), 0)
        self.assertEqual(auto_finalize_overdue_bookings(self._after(100)), 0)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.DISPUTED)

    def test_disputed_booking_cannot_be_confirmed(self):
        dispute_completion(self.booking, self.REASON)

        with self.assertRaises(ValidationError):
            confirm_completion(self.booking)

    def test_admin_can_finalize_a_disputed_booking(self):
        dispute_completion(self.booking, self.REASON)
        finalize_booking(self.booking)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, Booking.Status.FINALIZED)
        self.assertEqual(
            self.booking.finalization_method,
            Booking.FinalizationMethod.ADMIN,
        )
        self.assertIsNone(self.booking.job_address)

    def test_reopened_job_gets_fresh_reminders_and_timer(self):
        send_due_confirmation_reminders(self._after(24))
        dispute_completion(self.booking, self.REASON)

        reopen_booking(self.booking)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.IN_PROGRESS)
        self.assertIsNone(self.booking.completed_at)
        self.assertEqual(self.booking.dispute_reason, self.REASON)

        complete_booking(self.booking)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.confirmation_reminders_sent, 0)
        self.assertEqual(auto_finalize_overdue_bookings(self._after(71)), 0)
        self.assertEqual(auto_finalize_overdue_bookings(self._after(72)), 1)

    def test_only_disputed_bookings_can_be_reopened(self):
        with self.assertRaises(ValidationError):
            reopen_booking(self.booking)

    def test_disputed_booking_can_be_reviewed(self):
        from reviews.services import create_review

        dispute_completion(self.booking, self.REASON)

        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=2,
        )
        self.assertEqual(review.booking, self.booking)

    def test_non_text_dispute_reason_is_rejected_cleanly(self):
        for reason in (12345, ["The tap is still leaking badly."], {"a": 1}):
            with self.assertRaises(ValidationError):
                dispute_completion(self.booking, reason)

    def test_no_reminder_once_the_deadline_has_passed(self):
        self.assertEqual(send_due_confirmation_reminders(self._after(80)), 0)
        self.assertEqual(len(mail.outbox), 0)

    def _admin(self, username, **extra):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
            role=User.Role.ADMIN,
            **extra,
        )

    def test_dispute_emails_every_active_admin(self):
        self._admin("admin1")
        self._admin("admin2")
        self._admin("former_admin", is_active=False)

        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with self.captureOnCommitCallbacks(execute=True):
                dispute_completion(self.booking, self.REASON)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            sorted(email.to), ["admin1@example.com", "admin2@example.com"]
        )
        self.assertIn(f"#{self.booking.id}", email.subject)
        self.assertIn(self.REASON, email.body)
        self.assertIn("Joe Plumbing", email.body)
        self.assertIn(f"/status/{self.booking.id}/reopen", email.body)

    def test_dispute_still_succeeds_if_the_email_fails(self):
        self._admin("admin1")

        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with patch("bookings.services.send_mail", side_effect=Exception("SMTP down")):
                with self.captureOnCommitCallbacks(execute=True):
                    dispute_completion(self.booking, self.REASON)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.DISPUTED)

    def test_no_dispute_email_when_dispute_is_rejected(self):
        self._admin("admin1")

        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(ValidationError):
                    dispute_completion(self.booking, "too short")

        self.assertEqual(len(mail.outbox), 0)


class BookingInputTests(TestCase):
    def setUp(self):
        from .serializers import BookingCreateSerializer

        self.serializer_class = BookingCreateSerializer
        artisan_user = User.objects.create_user(
            username="input_artisan",
            email="input_artisan@example.com",
            password="testpassword123",
            full_name="Input Artisan",
            role=User.Role.ARTISAN,
        )
        artisan = Artisan.objects.create(
            user=artisan_user,
            phone_number="08000000040",
            verification_status=Artisan.VerificationStatus.VERIFIED,
        )
        service = Service.objects.create(
            name="Input Plumbing",
            description="Plumbing work",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.base_data = {"artisan": artisan.pk, "service": service.pk}

    def test_location_modes_require_mode_specific_fields(self):
        current = self.serializer_class(data={
            **self.base_data,
            "job_location_type": "current",
        })
        self.assertFalse(current.is_valid())
        self.assertIn("job_latitude", current.errors)
        self.assertIn("job_longitude", current.errors)

        saved = self.serializer_class(data={
            **self.base_data,
            "job_location_type": "saved",
        })
        self.assertFalse(saved.is_valid())
        self.assertIn("job_location_id", saved.errors)

        custom = self.serializer_class(data={
            **self.base_data,
            "job_location_type": "custom",
        })
        self.assertFalse(custom.is_valid())
        self.assertIn("non_field_errors", custom.errors)

    def test_review_summary_does_not_reveal_status(self):
        from .serializers import BookingSummarySerializer

        self.assertNotIn("status", BookingSummarySerializer.Meta.fields)
