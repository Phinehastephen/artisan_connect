from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        BOOKING_REQUESTED = "BOOKING_REQUESTED", "Booking requested"
        BOOKING_ACCEPTED = "BOOKING_ACCEPTED", "Booking accepted"
        BOOKING_REJECTED = "BOOKING_REJECTED", "Booking rejected"
        BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking cancelled"
        BOOKING_STARTED = "BOOKING_STARTED", "Work started"
        BOOKING_COMPLETED = "BOOKING_COMPLETED", "Work completed"
        BOOKING_CONFIRMATION_REMINDER = "BOOKING_CONFIRMATION_REMINDER", "Completion reminder"
        BOOKING_DISPUTED = "BOOKING_DISPUTED", "Booking disputed"
        BOOKING_FINALIZED = "BOOKING_FINALIZED", "Booking finalized"
        BOOKING_REOPENED = "BOOKING_REOPENED", "Booking reopened"
        REVIEW_RECEIVED = "REVIEW_RECEIVED", "Review received"
        SERVICE_CHANGE_REQUESTED = "SERVICE_CHANGE_REQUESTED", "Service change requested"
        SERVICE_CHANGE_APPROVED = "SERVICE_CHANGE_APPROVED", "Service change approved"
        SERVICE_CHANGE_REJECTED = "SERVICE_CHANGE_REJECTED", "Service change rejected"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=32, choices=Type.choices)
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=500)
    target_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["recipient", "read_at"]),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"{self.get_type_display()} for {self.recipient}"
