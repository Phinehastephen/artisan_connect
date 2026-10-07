from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
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
            "Plumbing", ["plumber", "pipe", "leak", "tap", "bathroom", "leaking pipe"]
        )
        self.electrical = make_service(
            "Electrical", ["electrician", "socket", "wiring", "sparking"]
        )
        self.carpentry = make_service("Carpentry", ["carpenter", "door", "roof"])

    def assertConfident(self, query, service):
        result = match_service(query)
        self.assertEqual(result.confidence, SearchLog.Confidence.CONFIDENT, query)
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
        ServiceKeyword.objects.create(service=self.electrical, keyword="switch")

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
        self.assertConfident("my ac is not cooling", Service.objects.get(name="AC & Refrigeration"))

    def test_vehicle_words_without_auto_repair_fall_back_to_scoring(self):
        Service.objects.filter(name="Auto Repair").delete()

        self.assertConfident("car socket sparking", self.electrical)

    def test_vague_query_needs_clarifying(self):
        for query in ("I need help with something", "help", "fix it please"):
            result = match_service(query)
            self.assertEqual(result.confidence, SearchLog.Confidence.NONE, query)
            self.assertIsNone(result.service)

    def test_unknown_words_match_nothing(self):
        self.assertEqual(match_service("xyzzy").confidence, SearchLog.Confidence.NONE)

    def test_close_scores_are_unsure_with_suggestions(self):
        result = match_service("the roof is leaking")

        self.assertEqual(result.confidence, SearchLog.Confidence.UNSURE)
        self.assertIsNone(result.service)
        self.assertEqual(set(result.suggestions), {self.carpentry, self.plumbing})

    def test_suggestions_are_capped_at_three(self):
        for name, word in (("Painting", "paint"), ("Cleaning", "clean")):
            make_service(name, [word])
        result = match_service("door socket tap paint clean")

        self.assertEqual(result.confidence, SearchLog.Confidence.UNSURE)
        self.assertEqual(len(result.suggestions), 3)

    def test_inactive_services_are_never_matched(self):
        make_service("Welding", ["welder", "gate"], is_active=False)

        self.assertEqual(match_service("welder").confidence, SearchLog.Confidence.NONE)
        self.assertEqual(match_service("Welding").confidence, SearchLog.Confidence.NONE)

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
        log = log_search(self.customer, "burst pipe", match_service("burst pipe"))

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
