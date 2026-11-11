from django.core.exceptions import ValidationError
from django.db import models


class Service(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    minimum_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    maximum_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def clean(self):
        if (
            self.minimum_price is not None
            and self.maximum_price is not None
            and self.minimum_price > self.maximum_price
        ):
            raise ValidationError(
                "Minimum price cannot be greater than maximum price."
            )

    def __str__(self):
        return self.name

class ServiceKeyword(models.Model):
    # Alternative words customers use for a service ("pipe", "leaking tap"
    # -> Plumbing). Kept out of Service so the frozen table stays as it is
    # and admins can add words without a code change.
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="keywords",
    )

    keyword = models.CharField(
        max_length=100,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["service", "keyword"],
                name="unique_keyword_per_service",
            ),
        ]

    def save(self, *args, **kwargs):
        from .text import normalize_text

        self.keyword = normalize_text(self.keyword)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.keyword} -> {self.service.name}"


class ServiceScopeQuestion(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="scope_questions",
    )
    key = models.SlugField(max_length=100)
    label = models.CharField(max_length=150)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "key"],
                name="unique_scope_question_key_per_service",
            ),
        ]

    def __str__(self):
        return f"{self.service.name}: {self.label}"


class ServiceScopeOption(models.Model):
    question = models.ForeignKey(
        ServiceScopeQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    value = models.SlugField(max_length=100)
    label = models.CharField(max_length=150)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "value"],
                name="unique_scope_option_value_per_question",
            ),
        ]

    def __str__(self):
        return f"{self.question.label}: {self.label}"
