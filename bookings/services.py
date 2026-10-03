import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import Booking

logger = logging.getLogger(__name__)

AUTO_FINALIZE_AFTER = timedelta(hours=72)
CONFIRMATION_REMINDER_SCHEDULE = [
    timedelta(hours=24),
    timedelta(hours=48),
    timedelta(hours=66),
]



JOB_LOCATION_FIELDS = ["job_address", "job_latitude", "job_longitude"]


def _clear_job_location(booking):
    """Erase the customer's job location once a booking is closed, so it
    isn't kept around (or exposed) after the artisan no longer needs it."""
    booking.job_address = None
    booking.job_latitude = None
    booking.job_longitude = None


def _lock(booking):
    # Re-read the row under a lock so two simultaneous transitions (e.g. a
    # customer cancelling while the artisan starts the job) can't both pass
    # their status check.
    Booking.objects.select_for_update().filter(pk=booking.pk).first()
    booking.refresh_from_db()


@transaction.atomic
def accept_booking(booking):
    """
    Transitions booking status from PENDING to ACCEPTED.
    """
    _lock(booking)

    if booking.status != Booking.Status.PENDING:
        raise ValidationError("Only pending bookings can be accepted.")
        
    booking.status = Booking.Status.ACCEPTED
    booking.accepted_at = timezone.now()
    booking.save(update_fields=["status", "accepted_at"])
    return booking


@transaction.atomic
def start_booking(booking):
    """
    Transitions booking status from ACCEPTED to IN_PROGRESS.
    """
    _lock(booking)

    if booking.status != Booking.Status.ACCEPTED:
        raise ValidationError("Only accepted bookings can be started.")
        
    booking.status = Booking.Status.IN_PROGRESS
    booking.save(update_fields=["status"])
    return booking


@transaction.atomic
def complete_booking(booking):
    """
    Transitions booking status from IN_PROGRESS to COMPLETED.
    """
    _lock(booking)

    if booking.status != Booking.Status.IN_PROGRESS:
        raise ValidationError("Only in-progress bookings can be completed.")
        
    booking.status = Booking.Status.COMPLETED
    booking.completed_at = timezone.now()
    booking.save(update_fields=["status", "completed_at"])
    return booking


@transaction.atomic
def reject_booking(booking):
    """
    Artisan declines a pending booking request.
    """
    _lock(booking)

    if booking.status != Booking.Status.PENDING:
        raise ValidationError("Only pending bookings can be rejected.")

    booking.status = Booking.Status.CANCELLED
    _clear_job_location(booking)
    booking.save(update_fields=["status", *JOB_LOCATION_FIELDS])
    return booking


@transaction.atomic
def cancel_booking(booking):
    """
    Customer withdraws a booking before work has started.
    """
    _lock(booking)

    if booking.status not in (Booking.Status.PENDING, Booking.Status.ACCEPTED):
        raise ValidationError(
            "Only pending or accepted bookings can be cancelled."
        )

    booking.status = Booking.Status.CANCELLED
    _clear_job_location(booking)
    booking.save(update_fields=["status", *JOB_LOCATION_FIELDS])
    return booking


def _finalize(booking, method):
    booking.status = Booking.Status.FINALIZED
    booking.finalized_at = timezone.now()
    booking.finalization_method = method
    _clear_job_location(booking)

    booking.save(update_fields=[
        "status",
        "finalized_at",
        "finalization_method",
        *JOB_LOCATION_FIELDS,
    ])
    return booking


@transaction.atomic
def confirm_completion(booking):
    _lock(booking)

    if booking.status != Booking.Status.COMPLETED:
        raise ValidationError(
            "Only bookings the artisan has marked complete can be confirmed."
        )

    return _finalize(booking, Booking.FinalizationMethod.CUSTOMER_CONFIRMED)


@transaction.atomic
def finalize_booking(booking):
    # Admin override, e.g. to settle a dispute.
    _lock(booking)

    if booking.status != Booking.Status.COMPLETED:
        raise ValidationError("Only completed bookings can be finalized.")

    return _finalize(booking, Booking.FinalizationMethod.ADMIN)


def _send_confirmation_reminder(booking, is_final):
    artisan_name = booking.artisan.business_name or booking.artisan.user.full_name
    deadline = booking.completed_at + AUTO_FINALIZE_AFTER

    try:
        send_mail(
            subject="Please confirm your completed Artisan Connect job",
            message=(
                f"{artisan_name} has marked your {booking.service.name} job "
                f"(booking #{booking.id}) as complete.\n\n"
                "Please open Artisan Connect to confirm it, or leave a review. "
                + ("This is your final reminder. " if is_final else "")
                + "If you don't respond, the booking will be confirmed "
                f"automatically on {deadline:%d %b %Y at %H:%M} UTC."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.customer.user.email],
        )
        return True
    except Exception:
        logger.exception(
            "Failed to send confirmation reminder for booking %s", booking.id
        )
        return False


def send_due_confirmation_reminders(now=None):
    now = now or timezone.now()
    sent = 0

    candidates = Booking.objects.filter(
        status=Booking.Status.COMPLETED,
        confirmation_reminders_sent__lt=len(CONFIRMATION_REMINDER_SCHEDULE),
    ).values_list("pk", flat=True)

    for pk in candidates:
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update(skip_locked=True, of=("self",))
                .select_related("customer__user", "artisan__user", "service")
                .filter(pk=pk, status=Booking.Status.COMPLETED)
                .first()
            )
            if booking is None:
                continue

            index = booking.confirmation_reminders_sent
            if index >= len(CONFIRMATION_REMINDER_SCHEDULE):
                continue
            if now < booking.completed_at + CONFIRMATION_REMINDER_SCHEDULE[index]:
                continue

            is_final = index == len(CONFIRMATION_REMINDER_SCHEDULE) - 1
            
            if _send_confirmation_reminder(booking, is_final):
                booking.confirmation_reminders_sent = index + 1
                booking.save(update_fields=["confirmation_reminders_sent"])
                sent += 1

    return sent


def auto_finalize_overdue_bookings(now=None):
    now = now or timezone.now()
    finalized = 0

    overdue = Booking.objects.filter(
        status=Booking.Status.COMPLETED,
        completed_at__lte=now - AUTO_FINALIZE_AFTER,
    ).values_list("pk", flat=True)

    for pk in overdue:
        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update(skip_locked=True)
                .filter(pk=pk, status=Booking.Status.COMPLETED)
                .first()
            )
            if booking is None:
                continue

            _finalize(booking, Booking.FinalizationMethod.AUTO)
            finalized += 1

    return finalized


@transaction.atomic
def create_booking(
    customer,
    artisan,
    service,
    job_address,
    job_latitude,
    job_longitude,
):
    if artisan.verification_status != "VERIFIED":
        raise ValidationError(
            "Only verified artisans can receive bookings."
        )

    if not service.is_active:
        raise ValidationError(
            "This service is no longer available."
        )

    if not artisan.services.filter(id=service.id).exists():
        raise ValidationError(
            "This artisan does not provide the selected service."
        )

    booking = Booking.objects.create(
        customer=customer,
        artisan=artisan,
        service=service,
        job_address=job_address,
        job_latitude=job_latitude,
        job_longitude=job_longitude,
        status=Booking.Status.PENDING,
    )

    return booking