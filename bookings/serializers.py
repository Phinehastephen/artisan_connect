from rest_framework import serializers
from .models import Booking
from customers.serializers import CustomerSerializer
from artisans.serializers import ArtisanSerializer
from services.serializers import ServiceSerializer


class BookingSerializer(serializers.ModelSerializer):
    """Serializer matching the precise Booking model schema."""

    # Read-only nested representations for response details
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    artisan_detail = ArtisanSerializer(source="artisan", read_only=True)
    service_detail = ServiceSerializer(source="service", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "customer",
            "artisan",
            "service",
            "customer_detail",
            "artisan_detail",
            "service_detail",
            "job_address",
            "job_latitude",
            "job_longitude",
            "status",
            "created_at",
            "updated_at",
            "accepted_at",
            "completed_at",
            "finalized_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "accepted_at",
            "completed_at",
            "finalized_at",
        ]

    def validate(self, data):
        """Custom validations for booking creation."""
        artisan = data.get("artisan")
        if artisan and hasattr(artisan, "is_verified") and not artisan.is_verified:
            raise serializers.ValidationError(
                {"artisan": "Bookings can only be created for verified artisans."}
            )
        return data