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