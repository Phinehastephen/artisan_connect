from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Review


@transaction.atomic
def create_review(
    booking,
    customer,
    rating,
    comment=None,
):
    if booking.customer_id != customer.id:
        raise ValidationError(
            "You can only review your own booking."
        )

    if booking.status != "COMPLETED":
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

    return Review.objects.create(
        booking=booking,
        customer=booking.customer,
        artisan=booking.artisan,
        rating=rating,
        comment=comment,
    )
    
@transaction.atomic
def edit_review(review, customer, rating, comment=None):
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