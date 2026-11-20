import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Without this a superuser gets the default CUSTOMER role, which the
        # app's IsAdmin permission rejects.
        extra_fields.setdefault("role", "ADMIN")
        return super().create_superuser(username, email, password, **extra_fields)


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

    objects = UserManager()

    def clean(self):
        super().clean()
        # Lowercase before Django's unique check runs, so admin forms reject
        # "TAKEN@x.com" when "taken@x.com" exists instead of crashing on save.
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        # Registration already lowercases, but admin and createsuperuser
        # don't go through it.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


EMAIL_VERIFICATION_TOKEN_TTL = timedelta(hours=24)


def _generate_email_verification_token():
    return secrets.token_urlsafe(32)


def _default_email_verification_expiry():
    return timezone.now() + EMAIL_VERIFICATION_TOKEN_TTL


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_email_verification_token,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(
        default=_default_email_verification_expiry,
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    def __str__(self):
        return f"Email verification token for {self.user.username}"

PASSWORD_RESET_CODE_TTL = timedelta(minutes=10)
PASSWORD_RESET_TOKEN_TTL = timedelta(minutes=15)
PASSWORD_RESET_MAX_ATTEMPTS = 5


def _default_password_reset_expiry():
    return timezone.now() + PASSWORD_RESET_CODE_TTL


class PasswordResetToken(models.Model):
    """
    Two-step password reset: a 6-digit code is emailed to the user, and
    once verified it's exchanged for a single-use reset_token that
    authorizes setting the new password.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )

    # Hashed like a password so a DB leak doesn't expose live codes.
    code_hash = models.CharField(max_length=128)

    attempts = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(
        default=_default_password_reset_expiry,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reset_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def code_is_usable(self):
        return (
            self.used_at is None
            and self.verified_at is None
            and self.attempts < PASSWORD_RESET_MAX_ATTEMPTS
            and timezone.now() < self.expires_at
        )

    def reset_token_is_usable(self):
        return (
            self.used_at is None
            and self.verified_at is not None
            and timezone.now() < self.verified_at + PASSWORD_RESET_TOKEN_TTL
        )

    def __str__(self):
        return f"Password reset token for {self.user.username}"
