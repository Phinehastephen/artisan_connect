from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ARTISAN = "ARTISAN", "Artisan"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)

    full_name = models.CharField(
        max_length=150
    )

    full_name_updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    email_verified = models.BooleanField(
        default=False
    )

    profile_picture = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    profile_picture_updated_at = models.DateTimeField(
        null=True,
        blank=True,
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

    def __str__(self):
        return self.username