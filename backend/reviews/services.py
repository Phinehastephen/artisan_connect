from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from bookings.models import Booking
from notifications.models import Notification
from notifications.services import create_notification

from .models import Review


@transaction.atomic
def create_review(
    booking,
    customer,
    rating,
    comment=None,
):
    Booking.objects.select_for_update().filter(pk=booking.pk).first()
    booking.refresh_from_db()

    if booking.customer_id != customer.id:
        raise ValidationError(
            "You can only review your own booking."
        )

    if booking.status not in ("COMPLETED", "DISPUTED", "FINALIZED"):
        raise ValidationError(
            "Only completed bookings can be reviewed."
        )

    if Review.objects.filter(booking=booking).exists():
        raise ValidationError(
            "This booking has already been reviewed."
        )

    if rating < 1 or rating > 5:
        raise ValidationError(
            "Rating must be between 1 and 5."
        )

    review = Review.objects.create(
        booking=booking,
        customer=booking.customer,
        artisan=booking.artisan,
        rating=rating,
        comment=comment,
    )
    artisan_user = booking.artisan.user
    create_notification(
        recipient=artisan_user,
        notification_type=Notification.Type.REVIEW_RECEIVED,
        title="New review received",
        message=f"You received a {rating}-star review for booking #{booking.pk}.",
        target_path=f"/api/v1/reviews/edit/{review.pk}",
    )
    return review


@transaction.atomic
def edit_review(review, customer, rating, comment=None):
    Review.objects.select_for_update().filter(pk=review.pk).first()
    review.refresh_from_db()

    if review.customer_id != customer.id:
        raise ValidationError(
            "You can only edit your own review."
        )

    if review.edited:
        raise ValidationError(
            "This review has already been edited."
        )

    if timezone.now() > review.created_at + timedelta(hours=24):
        raise ValidationError(
            "The 24-hour review editing period has expired."
        )

    if rating < 1 or rating > 5:
        raise ValidationError(
            "Rating must be between 1 and 5."
        )

    review.rating = rating
    review.comment = comment
    review.edited = True

    review.save(
        update_fields=[
            "rating",
            "comment",
            "edited",
            "updated_at",
        ]
    )

    return review
