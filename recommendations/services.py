from django.db.models import Avg, Count, Q, F, ExpressionWrapper, DurationField
from django.db.models.functions import Extract

from decimal import Decimal
from bookings.models import Booking
from reviews.models import Review

from artisans.models import Artisan
from locations.services import find_nearby_artisans


# Average of an artisan's reviews (+35 points)
def calculate_rating_score(average_rating):
    """Return a rating score out of 35 points."""

    if average_rating is None:
        return 0.0

    rating = Decimal(str(average_rating))

    if rating < Decimal("1.0") or rating > Decimal("5.0"):
        raise ValueError("Average rating must be between 1.0 and 5.0.")

    return round(float(rating / Decimal("5.0") * Decimal("35")), 2)


# Average number of completed jobs (+25 points)
def calculate_completed_jobs_score(completed_jobs):
    """Return an experience score out of 25 points."""

    if completed_jobs < 0:
        raise ValueError("Completed jobs cannot be negative.")

    if completed_jobs < 5:
        return 0
    elif completed_jobs < 15:
        return 5
    elif completed_jobs < 35:
        return 10
    elif completed_jobs < 75:
        return 15
    elif completed_jobs < 150:
        return 20

    return 25


# Total distance between the artisan and the customer (+25 points)
def calculate_distance_score(distance_km):
    """Return a proximity score out of 25 points."""

    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")

    if distance_km > 10:
        return 0

    if distance_km <= 2:
        return 25
    elif distance_km <= 4:
        return 20
    elif distance_km <= 6:
        return 15
    elif distance_km <= 8:
        return 10

    return 5


# Average response time in minutes (+15 points)
def calculate_response_time_score(average_response_minutes):
    """Return a response-time score out of 15 points."""

    if average_response_minutes is None:
        return 0

    if average_response_minutes < 0:
        raise ValueError("Response time cannot be negative.")

    if average_response_minutes <= 5:
        return 15
    elif average_response_minutes <= 15:
        return 12
    elif average_response_minutes <= 30:
        return 9
    elif average_response_minutes <= 60:
        return 6

    return 3


# Getting artisan's average rating, completed jobs, and average response time
def get_artisan_average_rating(artisan):
    """Return the artisan's average review rating, or None."""

    return Review.objects.filter(
        artisan=artisan,
        booking__status__in=[
            Booking.Status.COMPLETED,
            Booking.Status.DISPUTED,
            Booking.Status.FINALIZED,
        ],
    ).aggregate(
        average_rating=Avg("rating")
    )["average_rating"]


def get_artisan_completed_jobs(artisan):
    """Count successfully finalized bookings."""

    return Booking.objects.filter(
        artisan=artisan,
        status=Booking.Status.FINALIZED,
    ).count()


def get_artisan_average_response_minutes(artisan):
    """Return average acceptance time in minutes, or None."""

    response_times = Booking.objects.filter(
        artisan=artisan,
        accepted_at__isnull=False,
        created_at__isnull=False,
    ).annotate(
        response_duration=ExpressionWrapper(
            F("accepted_at") - F("created_at"),
            output_field=DurationField(),
        ),
    )

    durations = response_times.values_list(
        "response_duration",
        flat=True,
    )

    durations = [
        duration.total_seconds() / 60
        for duration in durations
        if duration.total_seconds() >= 0
    ]

    if not durations:
        return None

    return sum(durations) / len(durations)


def calculate_recommendation_score(artisan, distance_km):
    """Calculate the artisan's total recommendation score out of 100."""

    average_rating = get_artisan_average_rating(artisan)
    completed_jobs = get_artisan_completed_jobs(artisan)
    average_response_minutes = get_artisan_average_response_minutes(artisan)

    rating_score = calculate_rating_score(average_rating)
    jobs_score = calculate_completed_jobs_score(completed_jobs)
    distance_score = calculate_distance_score(distance_km)
    response_score = calculate_response_time_score(
        average_response_minutes
    )

    total_score = round(
        rating_score
        + jobs_score
        + distance_score
        + response_score,
        2,
    )

    return {
        "artisan_id": artisan.id,
        "rating": (
            round(float(average_rating), 2)
            if average_rating is not None
            else None
        ),
        "completed_jobs": completed_jobs,
        "distance_km": round(float(distance_km), 2),
        "average_response_minutes": (
            round(average_response_minutes, 2)
            if average_response_minutes is not None
            else None
        ),
        "scores": {
            "rating": rating_score,
            "completed_jobs": jobs_score,
            "distance": distance_score,
            "response_time": response_score,
        },
        "total_score": total_score,
    }


def rank_artisans(latitude, longitude, service_id):
    """
    Return verified artisans offering the requested service,
    within the nearby radius, ranked by recommendation score.
    """

    nearby_artisans = find_nearby_artisans(latitude, longitude)

    ranked_artisans = []
    seen_artisan_ids = set()

    for item in nearby_artisans:
        artisan = item["artisan"]
        distance_km = item["distance_km"]

        if distance_km > 10:
            continue

        if artisan.id in seen_artisan_ids:
            continue
        seen_artisan_ids.add(artisan.id)

        # Eligibility checks
        if artisan.verification_status != Artisan.VerificationStatus.VERIFIED:
            continue

        if not artisan.services.filter(
            id=service_id,
            is_active=True,
        ).exists():
            continue

        score_data = calculate_recommendation_score(
            artisan=artisan,
            distance_km=distance_km,
        )

        ranked_artisans.append({
            "artisan": artisan,
            "distance_km": distance_km,
            **score_data,
        })

    # Highest total score first.
    # If scores tie, prefer the closer artisan.
    ranked_artisans.sort(
        key=lambda item: (
            -item["total_score"],
            item["distance_km"],
            item["artisan"].id,
        )
    )

    return ranked_artisans
