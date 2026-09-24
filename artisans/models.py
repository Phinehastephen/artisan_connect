from django.conf import settings
from django.db import models


class Artisan(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artisan_profile",
    )

    phone_number = models.CharField(max_length=20)

    business_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    business_name_updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    starting_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    maximum_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    default_location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    
    latitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    )

    longitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    )

    services = models.ManyToManyField(
        "services.Service",
        related_name="artisans",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name