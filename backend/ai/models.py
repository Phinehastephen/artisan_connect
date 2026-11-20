from django.db import models


class SearchLog(models.Model):
    # What customers searched and what Smart Search made of it. Used to spot
    # missing keywords and as training data for the V2 model. Kept 12 months
    # (purge_search_logs).
    class Confidence(models.TextChoices):
        CONFIDENT = "CONFIDENT", "Confident"
        UNSURE = "UNSURE", "Unsure"
        NONE = "NONE", "No match"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="search_logs",
        null=True,
        blank=True,
    )

    query = models.CharField(
        max_length=200,
    )

    matched_service = models.ForeignKey(
        "services.Service",
        on_delete=models.SET_NULL,
        related_name="search_logs",
        null=True,
        blank=True,
    )

    confidence = models.CharField(
        max_length=10,
        choices=Confidence.choices,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return f"{self.query!r} -> {self.confidence}"
