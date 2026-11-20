from datetime import timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from artisans.models import Artisan
from services.models import Service
from bookings.models import Booking

from .models import Review
from .services import create_review, edit_review


class ReviewBusinessLogicTests(TestCase):

    def setUp(self):
        customer_user = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="testpassword123",
        )

        self.customer = Customer.objects.create(
            user=customer_user,
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

        self.booking = Booking.objects.create(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            job_address="Test Address",
            job_latitude=6.524400,
            job_longitude=3.379200,
            status=Booking.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        
    def test_customer_can_review_completed_booking(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=4.5,
            comment="Excellent service.",
        )

        self.assertEqual(
            review.rating,
            4.5,
        )

        self.assertEqual(
            review.customer,
            self.customer,
        )

        self.assertEqual(
            review.artisan,
            self.artisan,
        )
        
    def test_incomplete_booking_cannot_be_reviewed(self):
        self.booking.status = Booking.Status.IN_PROGRESS
        self.booking.save()

        with self.assertRaises(ValidationError):
            create_review(
                booking=self.booking,
                customer=self.customer,
                rating=4.0,
                comment="Good service.",
            )
            
    def test_customer_cannot_review_someone_elses_booking(self):
        other_user = User.objects.create_user(
            username="customer2",
            email="customer2@example.com",
            password="testpassword123",
        )

        other_customer = Customer.objects.create(
            user=other_user,
        )

        with self.assertRaises(ValidationError):
            create_review(
                booking=self.booking,
                customer=other_customer,
                rating=5.0,
                comment="Great.",
            )
            
    def test_booking_cannot_have_two_reviews(self):
        create_review(
            booking=self.booking,
            customer=self.customer,
            rating=4.0,
            comment="Good service.",
        )

        with self.assertRaises(ValidationError):
            create_review(
                booking=self.booking,
                customer=self.customer,
                rating=5.0,
                comment="Changed my mind.",
            )
            
    def test_rating_must_be_between_one_and_five(self):
        with self.assertRaises(ValidationError):
            create_review(
                booking=self.booking,
                customer=self.customer,
                rating=0,
                comment="Bad.",
            )

        with self.assertRaises(ValidationError):
            create_review(
                booking=self.booking,
                customer=self.customer,
                rating=5.5,
                comment="Too high.",
            )
            
    def test_review_can_be_edited_within_24_hours(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=3.0,
            comment="Good.",
        )

        review.created_at = timezone.now() - timedelta(hours=23)
        review.save(update_fields=["created_at"])

        updated_review = edit_review(
            review=review,
            customer=self.customer,
            rating=4.5,
            comment="Very good.",
        )

        self.assertEqual(
            updated_review.rating,
            4.5,
        )

        self.assertTrue(
            updated_review.edited,
        )
    
    def test_review_cannot_be_edited_after_24_hours(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=3.0,
            comment="Good.",
        )

        review.created_at = timezone.now() - timedelta(hours=25)
        review.save(update_fields=["created_at"])

        with self.assertRaises(ValidationError):
            edit_review(
                review=review,
                customer=self.customer,
                rating=5.0,
                comment="Excellent.",
            )

    def test_review_can_only_be_edited_once(self):
        review = create_review(
            booking=self.booking,
            customer=self.customer,
            rating=3.0,
            comment="Good.",
        )

        edit_review(
            review=review,
            customer=self.customer,
            rating=4.0,
            comment="Better.",
        )

        with self.assertRaises(ValidationError):
            edit_review(
                review=review,
                customer=self.customer,
                rating=5.0,
                comment="Excellent.",
            )


class ReviewCreateAPITests(TestCase):
    def setUp(self):
        customer_user = User.objects.create_user(
            username="review_api_customer",
            email="review_api_customer@example.com",
            password="test-password",
            role=User.Role.CUSTOMER,
        )
        self.customer = Customer.objects.create(user=customer_user)
        artisan_user = User.objects.create_user(
            username="review_api_artisan",
            email="review_api_artisan@example.com",
            password="test-password",
            role=User.Role.ARTISAN,
        )
        self.artisan = Artisan.objects.create(
            user=artisan_user,
            phone_number="08000000000",
            verification_status=Artisan.VerificationStatus.VERIFIED,
        )
        self.service = Service.objects.create(
            name="Review API Plumbing",
            description="",
            minimum_price=1000,
            maximum_price=5000,
            is_active=True,
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            artisan=self.artisan,
            service=self.service,
            status=Booking.Status.FINALIZED,
            finalized_at=timezone.now(),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=customer_user)

    def test_customer_can_review_finalized_booking(self):
        bookings_response = self.client.get("/api/v1/bookings/list")
        self.assertEqual(bookings_response.status_code, 200)
        self.assertFalse(bookings_response.data[0]["has_review"])

        response = self.client.post(
            "/api/v1/reviews/review/create",
            {
                "booking": self.booking.id,
                "rating": "4.5",
                "comment": "Great work and professional service.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["rating"]), "4.5")
        self.assertEqual(Booking.objects.get(pk=self.booking.pk).review.rating, 4.5)

        bookings_response = self.client.get("/api/v1/bookings/list")
        self.assertTrue(bookings_response.data[0]["has_review"])