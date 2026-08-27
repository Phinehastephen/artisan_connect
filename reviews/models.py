from django.db import models


class Review(models.Model):
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="review",
    )

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="reviews",
    )

    artisan = models.ForeignKey(
        "artisans.Artisan",
        on_delete=models.PROTECT,
        related_name="reviews",
    )

    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
    )

    comment = models.TextField(
        blank=True,
        null=True,
    )

    edited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.artisan.user.full_name} - {self.rating}"