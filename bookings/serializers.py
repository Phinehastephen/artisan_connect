from rest_framework import serializers
from .models import Booking
from customers.serializers import CustomerPublicSerializer
from artisans.serializers import ArtisanPublicSerializer
from services.serializers import ServiceSerializer


class BookingSerializer(serializers.ModelSerializer):
    """Serializer matching the precise Booking model schema."""

    # Read-only nested representations for response details. These use the
    # "public" customer/artisan serializers (no phone_number) since the
    # customer and artisan on a booking are each other's counterparty here,
    # not the profile owner — phone numbers must never cross that boundary.
    customer_detail = CustomerPublicSerializer(source="customer", read_only=True)
    artisan_detail = ArtisanPublicSerializer(source="artisan", read_only=True)
    service_detail = ServiceSerializer(source="service", read_only=True)

    JOB_LOCATION_FIELDS = ("job_address", "job_latitude", "job_longitude")

    # The artisan only gets the job location while they actually need to
    # travel there: hidden while PENDING (they decide from distance/area),
    # and hidden again once the job is over, so it can't be used to reach
    # the customer outside the app.
    ARTISAN_LOCATION_VISIBLE_STATUSES = (
        Booking.Status.ACCEPTED,
        Booking.Status.IN_PROGRESS,
    )

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

    def _can_view_job_location(self, booking):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user is None or not user.is_authenticated:
            return False

        if user.role == user.Role.ADMIN:
            return True

        if booking.customer.user_id == user.id:
            return True

        return (
            booking.artisan.user_id == user.id
            and booking.status in self.ARTISAN_LOCATION_VISIBLE_STATUSES
        )

    def to_representation(self, booking):
        data = super().to_representation(booking)

        if not self._can_view_job_location(booking):
            for field in self.JOB_LOCATION_FIELDS:
                data[field] = None

        return data

    def validate(self, data):
        """Custom validations for booking creation."""
        artisan = data.get("artisan")
        if artisan and hasattr(artisan, "is_verified") and not artisan.is_verified:
            raise serializers.ValidationError(
                {"artisan": "Bookings can only be created for verified artisans."}
            )
        return data


class BookingSummarySerializer(serializers.ModelSerializer):
    """Minimal booking info for places visible beyond the two parties
    (e.g. reviews). Never includes the job location."""

    service_detail = ServiceSerializer(source="service", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "service_detail",
            "status",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
