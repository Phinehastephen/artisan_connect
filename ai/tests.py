from datetime import timedelta
from io import StringIO
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from artisans.models import Artisan
from accounts.models import User
from customers.models import Customer
from bookings.models import Booking
from locations.models import SavedLocation
from reviews.models import Review
from services.models import Service, ServiceKeyword

from .models import SearchLog
from .services import log_search, match_service


def make_service(name, keywords=(), is_active=True):
    service = Service.objects.create(
        name=name,
        description="",
        minimum_price=1000,
        maximum_price=5000,
        is_active=is_active,
    )
    for keyword in keywords:
        ServiceKeyword.objects.create(service=service, keyword=keyword)
    return service


class SmartSearchMatchingTests(TestCase):

    def setUp(self):
        # Start from a known vocabulary, not the services seeded by migrations.
        Service.objects.all().delete()
        self.plumbing = make_service(
            "Plumbing", ["plumber", "pipe", "leak",
                         "tap", "bathroom", "leaking pipe"]
        )
        self.electrical = make_service(
            "Electrical", ["electrician", "socket", "wiring", "sparking"]
        )
        self.carpentry = make_service(
            "Carpentry", ["carpenter", "door", "roof"])

    def assertConfident(self, query, service):
        result = match_service(query)
        self.assertEqual(result.confidence,
                         SearchLog.Confidence.CONFIDENT, query)
        self.assertEqual(result.service, service, query)

    def test_exact_service_name_ignoring_case_and_punctuation(self):
        self.assertConfident("Plumbing", self.plumbing)
        self.assertConfident("  ELECTRICAL!! ", self.electrical)

    def test_keyword_matches_its_service(self):
        self.assertConfident("plumber", self.plumbing)
        self.assertConfident("my socket is sparking", self.electrical)

    def test_word_forms_match_the_keyword(self):
        # "leaking" -> leak, "taps" -> tap
        self.assertConfident("my bathroom is leaking", self.plumbing)
        self.assertConfident("both taps", self.plumbing)

    def test_typos_are_tolerated(self):
        self.assertConfident("electrecian", self.electrical)
        self.assertConfident("plumbr", self.plumbing)

    def test_exact_keyword_beats_another_services_typo_match(self):
        # "switch" is close to "stitch" but is itself an Electrical keyword.
        make_service("Tailoring", ["stitch"])
        ServiceKeyword.objects.create(
            service=self.electrical, keyword="switch")

        self.assertConfident("switch", self.electrical)
        self.assertConfident("stitch", Service.objects.get(name="Tailoring"))

    def test_word_of_multi_word_service_name_matches(self):
        auto_repair = make_service("Auto Repair", ["mechanic"])

        self.assertConfident("auto", auto_repair)

    def test_anything_about_a_vehicle_is_auto_repair(self):
        auto_repair = make_service("Auto Repair", ["mechanic"])
        make_service("AC & Refrigeration", ["ac", "not cooling"])

        self.assertConfident("my car ac is not cooling", auto_repair)
        self.assertConfident("car wiring sparking", auto_repair)
        self.assertConfident("my ac is not cooling",
                             Service.objects.get(name="AC & Refrigeration"))

    def test_vehicle_words_without_auto_repair_fall_back_to_scoring(self):
        Service.objects.filter(name="Auto Repair").delete()

        self.assertConfident("car socket sparking", self.electrical)

    def test_vague_query_needs_clarifying(self):
        for query in ("I need help with something", "help", "fix it please"):
            result = match_service(query)
            self.assertEqual(result.confidence,
                             SearchLog.Confidence.NONE, query)
            self.assertIsNone(result.service)

    def test_unknown_words_match_nothing(self):
        self.assertEqual(match_service("xyzzy").confidence,
                         SearchLog.Confidence.NONE)

    def test_close_scores_are_unsure_with_suggestions(self):
        result = match_service("the roof is leaking")

        self.assertEqual(result.confidence, SearchLog.Confidence.UNSURE)
        self.assertIsNone(result.service)
        self.assertEqual(set(result.suggestions), {
                         self.carpentry, self.plumbing})

    def test_suggestions_are_capped_at_three(self):
        for name, word in (("Painting", "paint"), ("Cleaning", "clean")):
            make_service(name, [word])
        result = match_service("door socket tap paint clean")

        self.assertEqual(result.confidence, SearchLog.Confidence.UNSURE)
        self.assertEqual(len(result.suggestions), 3)

    def test_inactive_services_are_never_matched(self):
        make_service("Welding", ["welder", "gate"], is_active=False)

        self.assertEqual(match_service("welder").confidence,
                         SearchLog.Confidence.NONE)
        self.assertEqual(match_service("Welding").confidence,
                         SearchLog.Confidence.NONE)

    def test_keywords_are_stored_normalized(self):
        keyword = ServiceKeyword.objects.create(
            service=self.plumbing, keyword="  Blocked-DRAIN! "
        )

        self.assertEqual(keyword.keyword, "blocked drain")
        self.assertConfident("my drain is blocked drain", self.plumbing)


class SearchLogTests(TestCase):

    def setUp(self):
        user = User.objects.create_user(
            username="searcher",
            email="searcher@example.com",
            password="testpassword123",
        )
        self.customer = Customer.objects.create(user=user)
        self.plumbing = make_service("Plumbing", ["pipe"])

    def test_search_is_logged_with_customer_and_outcome(self):
        log = log_search(self.customer, "burst pipe",
                         match_service("burst pipe"))

        self.assertEqual(log.customer, self.customer)
        self.assertEqual(log.matched_service, self.plumbing)
        self.assertEqual(log.confidence, SearchLog.Confidence.CONFIDENT)

    def test_logs_older_than_twelve_months_are_purged(self):
        old = log_search(self.customer, "old", match_service("old"))
        recent = log_search(self.customer, "recent", match_service("recent"))
        SearchLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=370)
        )
        SearchLog.objects.filter(pk=recent.pk).update(
            created_at=timezone.now() - timedelta(days=300)
        )

        call_command("purge_search_logs", stdout=StringIO())

        self.assertFalse(SearchLog.objects.filter(pk=old.pk).exists())
        self.assertTrue(SearchLog.objects.filter(pk=recent.pk).exists())


class SmartSearchRankingTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        customer_user = User.objects.create_user(
            username="ranking_search_customer",
            email="ranking_search_customer@example.com",
            password="testpassword123",
            full_name="Ranking Search Customer",
            role=User.Role.CUSTOMER,
        )
        self.customer = Customer.objects.create(
            user=customer_user,
            phone_number="08000000020",
        )
        self.client.force_authenticate(user=customer_user)

        self.plumbing = make_service("Plumbing", ["pipe"])
        self.first_artisan = self.create_artisan("ranked_first")
        self.second_artisan = self.create_artisan("ranked_second")

    def create_artisan(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpassword123",
            full_name=username,
            role=User.Role.ARTISAN,
        )
        artisan = Artisan.objects.create(
            user=user,
            phone_number="08000000021",
            verification_status=Artisan.VerificationStatus.VERIFIED,
            starting_price=Decimal("1000.00"),
            maximum_price=Decimal("5000.00"),
            latitude=Decimal("6.524400"),
            longitude=Decimal("3.379200"),
        )
        artisan.services.add(self.plumbing)
        artisan.average_rating = None
        artisan.review_count = 0
        return artisan

    @patch("ai.views.rank_artisans")
    def test_smart_search_preserves_composite_ranker_order(self, mock_rank):
        mock_rank.return_value = [
            {
                "artisan": self.second_artisan,
                "distance_km": 3.0,
                "completed_jobs": 8,
                "average_response_minutes": 12.5,
                "scores": {"rating": 28.0, "distance": 20.0},
                "total_score": 72.0,
            },
            {
                "artisan": self.first_artisan,
                "distance_km": 2.0,
                "completed_jobs": 4,
                "average_response_minutes": None,
                "scores": {"rating": 35.0, "distance": 25.0},
                "total_score": 80.0,
            },
        ]

        response = self.client.get(
            "/api/v1/ai/search",
            {
                "q": "plumbing",
                "latitude": "6.5244",
                "longitude": "3.3792",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [self.second_artisan.id, self.first_artisan.id],
        )
        self.assertEqual(response.data["results"][0]["total_score"], 72.0)
        self.assertEqual(
            response.data["results"][0]["scores"],
            {"rating": 28.0, "distance": 20.0},
        )
        mock_rank.assert_called_once_with(
            latitude=6.5244,
            longitude=3.3792,
            service_id=self.plumbing.id,
        )

    def test_full_search_location_map_and_composite_ranking_flow(self):
        self.first_artisan.latitude = Decimal("6.524400")
        self.first_artisan.longitude = Decimal("3.379200")
        self.first_artisan.default_location = "Central Lagos"
        self.first_artisan.save(
            update_fields=["latitude", "longitude", "default_location"]
        )
        self.second_artisan.latitude = Decimal("6.524400")
        self.second_artisan.longitude = Decimal("3.379200")
        self.second_artisan.default_location = "Central Lagos"
        self.second_artisan.save(
            update_fields=["latitude", "longitude", "default_location"]
        )

        outside_artisan = self.create_artisan("ranked_outside")
        outside_artisan.longitude = Decimal("3.579200")
        outside_artisan.save(update_fields=["longitude"])

        def add_history(artisan, completed_jobs, rating):
            bookings = [
                Booking(
                    customer=self.customer,
                    artisan=artisan,
                    service=self.plumbing,
                    status=Booking.Status.FINALIZED,
                )
                for _ in range(completed_jobs)
            ]
            Booking.objects.bulk_create(bookings)
            Review.objects.create(
                booking=bookings[0],
                customer=self.customer,
                artisan=artisan,
                rating=Decimal(str(rating)),
            )

        add_history(self.first_artisan, 5, 4.7)
        add_history(self.second_artisan, 45, 3.7)

        saved_location = SavedLocation.objects.create(
            customer=self.customer,
            name="Home",
            address="Central Lagos",
            latitude=Decimal("6.524400"),
            longitude=Decimal("3.379200"),
        )

        current_response = self.client.get(
            "/api/v1/ai/search",
            {
                "q": "plumbing",
                "location_type": "current",
                "latitude": "6.5244",
                "longitude": "3.3792",
            },
        )
        saved_response = self.client.get(
            "/api/v1/ai/search",
            {
                "q": "pipe",
                "location_type": "saved",
                "location_id": str(saved_location.id),
            },
        )

        expected_order = [self.second_artisan.id, self.first_artisan.id]
        for location_mode, response in (
            ("current", current_response),
            ("saved", saved_response),
        ):
            with self.subTest(location_mode=location_mode):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["service"]["id"], self.plumbing.id)
                self.assertEqual(
                    response.data["origin"],
                    {"latitude": 6.5244, "longitude": 3.3792},
                )
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    expected_order,
                )
                results = response.data["results"]
                self.assertEqual(results[0]["total_score"], 65.9)
                self.assertEqual(results[1]["total_score"], 62.9)
                self.assertTrue(
                    all(item["distance_km"] <= 10 for item in results))
                self.assertTrue(
                    all("latitude" in item and "longitude" in item for item in results))
                self.assertTrue(all("scores" in item for item in results))
                self.assertNotIn(
                    outside_artisan.id,
                    [item["id"] for item in results],
                )
                for item in results:
                    self.assertNotIn("phone_number", item)
