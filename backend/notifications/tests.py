from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User
from artisans.models import Artisan, ServiceQualificationEvidence
from artisans.services import (
    approve_service_change_request,
    create_service_change_request,
)
from bookings.models import Booking
from bookings.services import (
    accept_booking,
    complete_booking,
    confirm_completion,
    create_booking,
    dispute_completion,
    reopen_booking,
    start_booking,
    send_due_confirmation_reminders,
)
from customers.models import Customer
from reviews.services import create_review
from services.models import Service

from .models import Notification
from .services import create_notification, notify_admins


class NotificationInboxTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="notification_user",
            email="notification-user@example.com",
            password="testpassword123",
            full_name="Notification User",
            role=User.Role.CUSTOMER,
        )
        self.other_user = User.objects.create_user(
            username="other_notification_user",
            email="other-notification-user@example.com",
            password="testpassword123",
            full_name="Other Notification User",
            role=User.Role.CUSTOMER,
        )
        self.base_url = "/api/v1/notifications/"

    def create_notice(self, recipient, message="A booking changed."):
        return create_notification(
            recipient=recipient,
            notification_type=Notification.Type.BOOKING_ACCEPTED,
            title="Booking update",
            message=message,
            target_path="/api/v1/bookings/details/12",
        )

    def test_list_only_returns_the_authenticated_users_notifications(self):
        own_notice = self.create_notice(self.user)
        self.create_notice(self.other_user, "Private to another account.")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["unread_count"], 1)
        self.assertEqual(response.data["results"][0]["id"], own_notice.id)

    def test_unread_filter_and_count(self):
        read_notice = self.create_notice(self.user)
        read_notice.read_at = read_notice.created_at
        read_notice.save(update_fields=["read_at"])
        self.create_notice(self.user, "Still unread.")
        self.client.force_authenticate(user=self.user)

        list_response = self.client.get(
            self.base_url,
            {"unread_only": "true"},
        )
        count_response = self.client.get(f"{self.base_url}unread-count")

        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["unread_count"], 1)
        self.assertEqual(count_response.data["unread_count"], 1)

    def test_user_can_mark_own_notice_read_but_not_another_users_notice(self):
        own_notice = self.create_notice(self.user)
        other_notice = self.create_notice(self.other_user)
        self.client.force_authenticate(user=self.user)

        forbidden_notice_response = self.client.post(
            f"{self.base_url}{other_notice.id}/read"
        )
        own_notice_response = self.client.post(
            f"{self.base_url}{own_notice.id}/read"
        )

        self.assertEqual(forbidden_notice_response.status_code, 404)
        self.assertEqual(own_notice_response.status_code, 200)
        self.assertTrue(own_notice_response.data["is_read"])

    def test_mark_all_read_only_updates_authenticated_user(self):
        own_notice = self.create_notice(self.user)
        other_notice = self.create_notice(self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f"{self.base_url}read-all")

        own_notice.refresh_from_db()
        other_notice.refresh_from_db()
        self.assertEqual(response.data["updated_count"], 1)
        self.assertTrue(own_notice.is_read)
        self.assertFalse(other_notice.is_read)

    def test_invalid_page_parameters_return_bad_request(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.base_url, {"page": "not-a-number"})

        self.assertEqual(response.status_code, 400)


class AdminNotificationTests(TestCase):
    def test_notify_admins_targets_only_active_admins(self):
        active_admin = User.objects.create_user(
            username="active_notification_admin",
            email="active-admin@example.com",
            password="testpassword123",
            full_name="Active Admin",
            role=User.Role.ADMIN,
        )
        User.objects.create_user(
            username="inactive_notification_admin",
            email="inactive-admin@example.com",
            password="testpassword123",
            full_name="Inactive Admin",
            role=User.Role.ADMIN,
            is_active=False,
        )
        User.objects.create_user(
            username="notification_customer",
            email="notification-customer@example.com",
            password="testpassword123",
            full_name="Customer",
            role=User.Role.CUSTOMER,
        )

        notices = notify_admins(
            notification_type=Notification.Type.BOOKING_DISPUTED,
            title="Dispute needs review",
            message="A booking was disputed.",
        )

        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].recipient_id, active_admin.id)


class NotificationEventIntegrationTests(TestCase):
    def setUp(self):
        self.customer_user = User.objects.create(
            username="event_customer",
            email="event-customer@example.com",
            full_name="Event Customer",
            role=User.Role.CUSTOMER,
        )
        self.customer = Customer.objects.create(
            user=self.customer_user,
            phone_number="08000000000",
        )
        self.artisan_user = User.objects.create(
            username="event_artisan",
            email="event-artisan@example.com",
            full_name="Event Artisan",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08000000001",
            verification_status=Artisan.VerificationStatus.VERIFIED,
        )
        self.admin = User.objects.create(
            username="event_admin",
            email="event-admin@example.com",
            full_name="Event Admin",
            role=User.Role.ADMIN,
        )
        self.service = Service.objects.create(
            name="Event Plumbing",
            description="Service used for notification tests",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.new_service = Service.objects.create(
            name="Event Electrical",
            description="Replacement service used for notification tests",
            minimum_price=2000,
            maximum_price=6000,
            is_active=True,
        )
        self.artisan.services.add(self.service)

    def tearDown(self):
        for evidence in ServiceQualificationEvidence.objects.all():
            evidence.file.delete(save=False)

    def test_booking_lifecycle_and_dispute_notify_the_relevant_users(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test address",
            job_latitude=6.5,
            job_longitude=3.3,
        )
        accept_booking(booking)
        start_booking(booking)
        complete_booking(booking)
        dispute_completion(
            booking, "The work is incomplete and needs correction.")
        reopen_booking(booking)
        complete_booking(booking)
        confirm_completion(booking)

        artisan_types = set(
            Notification.objects.filter(recipient=self.artisan_user)
            .values_list("type", flat=True)
        )
        customer_types = set(
            Notification.objects.filter(recipient=self.customer_user)
            .values_list("type", flat=True)
        )
        admin_types = set(
            Notification.objects.filter(recipient=self.admin)
            .values_list("type", flat=True)
        )

        self.assertTrue({
            Notification.Type.BOOKING_REQUESTED,
            Notification.Type.BOOKING_DISPUTED,
            Notification.Type.BOOKING_REOPENED,
            Notification.Type.BOOKING_FINALIZED,
        }.issubset(artisan_types))
        self.assertTrue({
            Notification.Type.BOOKING_ACCEPTED,
            Notification.Type.BOOKING_STARTED,
            Notification.Type.BOOKING_COMPLETED,
        }.issubset(customer_types))
        self.assertIn(Notification.Type.BOOKING_DISPUTED, admin_types)

    def test_review_notifies_the_artisan(self):
        booking = Booking.objects.create(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            status=Booking.Status.COMPLETED,
        )

        review = create_review(
            booking=booking,
            customer=self.customer,
            rating=4,
            comment="Good work.",
        )

        notice = Notification.objects.get(
            recipient=self.artisan_user,
            type=Notification.Type.REVIEW_RECEIVED,
        )
        self.assertIn(str(review.pk), notice.target_path)

    def test_successful_confirmation_reminder_creates_an_in_app_notice(self):
        booking = create_booking(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test address",
            job_latitude=6.5,
            job_longitude=3.3,
        )
        accept_booking(booking)
        start_booking(booking)
        complete_booking(booking)
        reminder_time = booking.completed_at + timedelta(hours=25)

        with patch("bookings.services._send_confirmation_reminder", return_value=True):
            sent = send_due_confirmation_reminders(now=reminder_time)

        self.assertEqual(sent, 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer_user,
                type=Notification.Type.BOOKING_CONFIRMATION_REMINDER,
            ).exists()
        )

    def test_service_change_submission_and_approval_notify_admin_and_artisan(self):
        request = create_service_change_request(
            artisan=self.artisan,
            service_ids=[self.new_service.id],
            qualification_evidence={
                "trade_certificate": [SimpleUploadedFile(
                    "certificate.pdf", b"%PDF-1.4\ncertificate",
                    content_type="application/pdf",
                )],
                "training_completion": [SimpleUploadedFile(
                    "training.jpg", b"\xff\xd8\xff\xe0training",
                    content_type="image/jpeg",
                )],
            },
            reason="I have completed the required training for electrical work.",
        )
        admin_notice = Notification.objects.get(
            recipient=self.admin,
            type=Notification.Type.SERVICE_CHANGE_REQUESTED,
        )

        approve_service_change_request(request)

        artisan_notice = Notification.objects.get(
            recipient=self.artisan_user,
            type=Notification.Type.SERVICE_CHANGE_APPROVED,
        )
        self.assertEqual(
            admin_notice.target_path,
            "/api/v1/artisans/service-change-requests",
        )
        self.assertIn(str(request.pk), artisan_notice.message)
