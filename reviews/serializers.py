from rest_framework import serializers
from .models import Review
from customers.serializers import CustomerSerializer
from artisans.serializers import ArtisanSerializer
from bookings.serializers import BookingSerializer


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer matching the exact Review model schema."""

    # Read-only nested representations for GET response details
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    artisan_detail = ArtisanSerializer(source="artisan", read_only=True)
    booking_detail = BookingSerializer(source="booking", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "booking",
            "customer",
            "artisan",
            "booking_detail",
            "customer_detail",
            "artisan_detail",
            "rating",
            "comment",
            "edited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "edited",
            "created_at",
            "updated_at",
        ]

    def validate_rating(self, value):
        """Ensure the rating falls between 1.0 and 5.0."""
        if value < 1.0 or value > 5.0:
            raise serializers.ValidationError("Rating must be between 1.0 and 5.0.")
        return value

    def update(self, instance, validated_data):
        """Automatically set edited=True whenever a review comment or rating is modified."""
        if "comment" in validated_data or "rating" in validated_data:
            instance.edited = True
        return super().update(instance, validated_data)