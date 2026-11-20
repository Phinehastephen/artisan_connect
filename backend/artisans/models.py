from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateQualificationEvidenceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=settings.PRIVATE_UPLOAD_ROOT / "service_qualification_evidence",
            base_url=None,
        )


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


class ServiceChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    artisan = models.ForeignKey(
        Artisan,
        on_delete=models.CASCADE,
        related_name="service_change_requests",
    )

    services = models.ManyToManyField(
        "services.Service",
        related_name="service_change_requests",
        blank=True,
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.artisan.user.full_name} - {self.status}"


class ServiceQualificationEvidence(models.Model):
    class Category(models.TextChoices):
        TRADE_CERTIFICATE = "trade_certificate", "Trade certificate or qualification"
        TRAINING_COMPLETION = "training_completion", "Training completion evidence"
        PORTFOLIO_EXPERIENCE = "portfolio_experience", "Portfolio or work experience evidence"

    service_change_request = models.ForeignKey(
        ServiceChangeRequest,
        on_delete=models.CASCADE,
        related_name="qualification_evidence",
    )
    category = models.CharField(max_length=32, choices=Category.choices)
    file = models.FileField(
        storage=PrivateQualificationEvidenceStorage(),
        upload_to="%Y/%m/",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.get_category_display()} for request #{self.service_change_request_id}"
