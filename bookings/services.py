from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Booking

@transaction.atomic
def create_booking(customer, artisan, service, job_address, job_latitude, job_longitude):
    """
    Creates a new booking after verifying the artisan provides the selected service.
    """
    if not artisan.services.filter(id=service.id).exists():
        raise ValidationError("This artisan does not provide the selected service.")
        
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


@transaction.atomic
def accept_booking(booking):
    """
    Transitions booking status from PENDING to ACCEPTED.
    """
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
    if booking.status != Booking.Status.IN_PROGRESS:
        raise ValidationError("Only in-progress bookings can be completed.")
        
    booking.status = Booking.Status.COMPLETED
    booking.completed_at = timezone.now()
    booking.save(update_fields=["status", "completed_at"])
    return booking


@transaction.atomic
def finalize_booking(booking):
    """
    Transitions booking status from COMPLETED to FINALIZED and strips precise location details for privacy.
    """
    if booking.status != Booking.Status.COMPLETED:
        raise ValidationError("Only completed bookings can be finalized.")
        
    booking.status = Booking.Status.FINALIZED
    booking.finalized_at = timezone.now()
    booking.job_address = None
    booking.job_latitude = None
    booking.job_longitude = None
    
    booking.save(update_fields=[
        "status", 
        "finalized_at", 
        "job_address", 
        "job_latitude", 
        "job_longitude"
    ])
    return booking

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