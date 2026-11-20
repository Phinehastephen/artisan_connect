from django.test import SimpleTestCase
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from artisans.models import Artisan
from services.models import Service
from customers.models import Customer
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .services import (
    calculate_rating_score,
    calculate_completed_jobs_score,
    calculate_distance_score,
    calculate_response_time_score,
    rank_artisans,
)


User = get_user_model()


class RecommendationScoringTests(SimpleTestCase):

    def test_rating_score(self):
        self.assertEqual(calculate_rating_score(5.0), 35.0)
        self.assertEqual(calculate_rating_score(4.0), 28.0)
        self.assertEqual(calculate_rating_score(None), 0.0)

    def test_completed_jobs_score(self):
        self.assertEqual(calculate_completed_jobs_score(0), 0)
        self.assertEqual(calculate_completed_jobs_score(10), 5)
        self.assertEqual(calculate_completed_jobs_score(20), 10)
        self.assertEqual(calculate_completed_jobs_score(100), 20)
        self.assertEqual(calculate_completed_jobs_score(670), 25)

    def test_distance_score(self):
        self.assertEqual(calculate_distance_score(1), 25)
        self.assertEqual(calculate_distance_score(3), 20)
        self.assertEqual(calculate_distance_score(5), 15)
        self.assertEqual(calculate_distance_score(7), 10)
        self.assertEqual(calculate_distance_score(9), 5)
        self.assertEqual(calculate_distance_score(10), 5)

    def test_response_time_score(self):
        self.assertEqual(calculate_response_time_score(3), 15)
        self.assertEqual(calculate_response_time_score(10), 12)
        self.assertEqual(calculate_response_time_score(20), 9)
        self.assertEqual(calculate_response_time_score(45), 6)
        self.assertEqual(calculate_response_time_score(90), 3)
        self.assertEqual(calculate_response_time_score(None), 0)


class ArtisanRankingTests(TestCase):

    def setUp(self):
        self.service = Service.objects.create(
            name="Electrician",
            description="Electrical repairs",
            minimum_price=Decimal("1000.00"),
            maximum_price=Decimal("10000.00"),
            is_active=True,
        )

        self.artisan_user = User.objects.create_user(
            username="artisan1",
            email="artisan1@example.com",
            password="TestPassword123!",
            full_name="Artisan One",
            role=User.Role.ARTISAN,
        )

        self.artisan = Artisan.objects.create(
            user=self.artisan_user,
            phone_number="08000000001",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude=Decimal("6.524400"),
            longitude=Decimal("3.379200"),
        )
        self.artisan.services.add(self.service)

    @patch("recommendations.services.find_nearby_artisans")
    def test_verified_artisan_with_requested_service_is_ranked(self, mock_nearby):
        mock_nearby.return_value = [
            {
                "artisan": self.artisan,
                "distance_km": 2.0,
            }
        ]

        results = rank_artisans(
            latitude=6.5244,
            longitude=3.3792,
            service_id=self.service.id,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["artisan"], self.artisan)
        self.assertIn("total_score", results[0])

    @patch("recommendations.services.find_nearby_artisans")
    def test_duplicate_artisan_is_ranked_only_once(self, mock_nearby):
        mock_nearby.return_value = [
            {"artisan": self.artisan, "distance_km": 2.0},
            {"artisan": self.artisan, "distance_km": 2.0},
        ]

        results = rank_artisans(
            latitude=6.5244,
            longitude=3.3792,
            service_id=self.service.id,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["artisan"], self.artisan)

    @patch("recommendations.services.find_nearby_artisans")
    def test_artisan_without_requested_service_is_excluded(self, mock_nearby):
        mock_nearby.return_value = [
            {
                "artisan": self.artisan,
                "distance_km": 2.0,
            }
        ]

        results = rank_artisans(
            latitude=6.5244,
            longitude=3.3792,
            service_id=99999,
        )

        self.assertEqual(results, [])

    @patch("recommendations.services.find_nearby_artisans")
    def test_unverified_artisan_is_excluded(self, mock_nearby):
        self.artisan.verification_status = Artisan.VerificationStatus.PENDING
        self.artisan.save(update_fields=["verification_status"])

        mock_nearby.return_value = [
            {
                "artisan": self.artisan,
                "distance_km": 2.0,
            }
        ]

        results = rank_artisans(
            latitude=6.5244,
            longitude=3.3792,
            service_id=self.service.id,
        )

        self.assertEqual(results, [])

    @patch("recommendations.services.calculate_recommendation_score")
    @patch("recommendations.services.find_nearby_artisans")
    def test_higher_score_ranks_first(
        self, mock_nearby, mock_score
    ):
        # Create a second verified artisan offering the same service.
        second_user = User.objects.create_user(
            username="artisan2",
            email="artisan2@example.com",
            password="TestPassword123!",
            full_name="Artisan Two",
            role=User.Role.ARTISAN,
        )

        second_artisan = Artisan.objects.create(
            user=second_user,
            phone_number="08000000002",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude=Decimal("6.530000"),
            longitude=Decimal("3.380000"),
        )
        second_artisan.services.add(self.service)

        mock_nearby.return_value = [
            {"artisan": self.artisan, "distance_km": 2.0},
            {"artisan": second_artisan, "distance_km": 4.0},
        ]

        def score_by_artisan(artisan, distance_km):
            score = 70 if artisan.id == self.artisan.id else 90
            return {"total_score": score}

        mock_score.side_effect = score_by_artisan

        results = rank_artisans(6.5244, 3.3792, self.service.id)

        self.assertEqual(results[0]["artisan"], second_artisan)
        self.assertEqual(results[0]["total_score"], 90)
        self.assertEqual(results[1]["artisan"], self.artisan)

    @patch("recommendations.services.calculate_recommendation_score")
    @patch("recommendations.services.find_nearby_artisans")
    def test_closer_artisan_wins_score_tie(
        self, mock_nearby, mock_score
    ):
        second_user = User.objects.create_user(
            username="artisan2",
            email="artisan2@example.com",
            password="TestPassword123!",
            full_name="Artisan Two",
            role=User.Role.ARTISAN,
        )

        second_artisan = Artisan.objects.create(
            user=second_user,
            phone_number="08000000002",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude=Decimal("6.530000"),
            longitude=Decimal("3.380000"),
        )
        second_artisan.services.add(self.service)

        mock_nearby.return_value = [
            {"artisan": self.artisan, "distance_km": 4.0},
            {"artisan": second_artisan, "distance_km": 2.0},
        ]

        mock_score.return_value = {"total_score": 80}

        results = rank_artisans(6.5244, 3.3792, self.service.id)

        self.assertEqual(results[0]["artisan"], second_artisan)
        self.assertEqual(results[1]["artisan"], self.artisan)

    @patch("recommendations.services.calculate_recommendation_score")
    @patch("recommendations.services.find_nearby_artisans")
    def test_lower_artisan_id_wins_when_score_and_distance_tie(
        self, mock_nearby, mock_score
    ):
        second_user = User.objects.create_user(
            username="artisan2",
            email="artisan2@example.com",
            password="TestPassword123!",
            full_name="Artisan Two",
            role=User.Role.ARTISAN,
        )

        second_artisan = Artisan.objects.create(
            user=second_user,
            phone_number="08000000002",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude=Decimal("6.530000"),
            longitude=Decimal("3.380000"),
        )
        second_artisan.services.add(self.service)

        mock_nearby.return_value = [
            {"artisan": second_artisan, "distance_km": 3.0},
            {"artisan": self.artisan, "distance_km": 3.0},
        ]

        mock_score.return_value = {"total_score": 80}

        results = rank_artisans(6.5244, 3.3792, self.service.id)

        self.assertLess(self.artisan.id, second_artisan.id)
        self.assertEqual(results[0]["artisan"], self.artisan)
        self.assertEqual(results[1]["artisan"], second_artisan)


class RecommendationAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.customer_user = User.objects.create_user(
            username="customer_api",
            email="customer_api@example.com",
            password="TestPassword123!",
            full_name="Test Customer",
            role=User.Role.CUSTOMER,
        )

        # IsCustomer requires a linked profile (user.customer_profile),
        # just like registration creates one.
        Customer.objects.create(user=self.customer_user)

        self.admin_user = User.objects.create_user(
            username="admin_api",
            email="admin_api@example.com",
            password="TestPassword123!",
            full_name="Test Admin",
            role=User.Role.ADMIN,
        )

        self.service = Service.objects.create(
            name="API Test Electrician",
            description="Electrical repairs",
            minimum_price=Decimal("1000.00"),
            maximum_price=Decimal("10000.00"),
            is_active=True,
        )

        artisan_user = User.objects.create_user(
            username="artisan_api",
            email="artisan_api@example.com",
            password="TestPassword123!",
            full_name="Test Artisan",
            role=User.Role.ARTISAN,
        )

        self.artisan = Artisan.objects.create(
            user=artisan_user,
            phone_number="08000000003",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            latitude=Decimal("6.524400"),
            longitude=Decimal("3.379200"),
        )
        self.artisan.services.add(self.service)

        self.url = reverse("recommendation-list")

        self.params = {
            "service_id": self.service.id,
            "latitude": "6.5244",
            "longitude": "3.3792",
        }

    def authenticate_as(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    def test_unauthenticated_user_is_rejected(self):
        response = self.client.get(self.url, self.params)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_artisan_cannot_access_customer_endpoint(self):
        artisan_user = User.objects.get(username="artisan_api")
        self.authenticate_as(artisan_user)

        response = self.client.get(self.url, self.params)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_cannot_access_customer_endpoint(self):
        self.authenticate_as(self.admin_user)

        response = self.client.get(self.url, self.params)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_latitude_is_rejected(self):
        self.authenticate_as(self.customer_user)

        params = {**self.params, "latitude": "95"}

        response = self.client.get(self.url, params)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_longitude_is_rejected(self):
        self.authenticate_as(self.customer_user)

        params = {**self.params, "longitude": "200"}

        response = self.client.get(self.url, params)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_nonexistent_service_is_rejected(self):
        self.authenticate_as(self.customer_user)

        params = {**self.params, "service_id": 999999}

        response = self.client.get(self.url, params)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_inactive_service_is_rejected(self):
        self.authenticate_as(self.customer_user)

        self.service.is_active = False
        self.service.save(update_fields=["is_active"])

        response = self.client.get(self.url, self.params)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_returned_scores_are_between_zero_and_100(self):
        self.authenticate_as(self.customer_user)

        response = self.client.get(self.url, self.params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for result in response.data:
            self.assertGreaterEqual(result["total_score"], 0)
            self.assertLessEqual(result["total_score"], 100)

    def test_results_are_sorted_by_total_score(self):
        self.authenticate_as(self.customer_user)

        response = self.client.get(self.url, self.params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        scores = [result["total_score"] for result in response.data]

        self.assertEqual(scores, sorted(scores, reverse=True))

    @patch("recommendations.services.find_nearby_artisans")
    def test_artisan_beyond_10km_is_excluded(self, mock_nearby):
        self.authenticate_as(self.customer_user)

        mock_nearby.return_value = [
            {
                "artisan": self.artisan,
                "distance_km": 2.0,
            },
            {
                "artisan": self.artisan,
                "distance_km": 12.0,
            },
        ]

        response = self.client.get(self.url, self.params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            all(
                result["distance_km"] <= 10
                for result in response.data
            )
        )
