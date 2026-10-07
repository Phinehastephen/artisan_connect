from rest_framework import serializers
from .models import Booking
from artisans.models import Artisan
from services.models import Service
from locations.serializers import CoordinateField
from customers.serializers import CustomerPublicSerializer
from artisans.serializers import ArtisanPublicSerializer
from services.serializers import ServiceSerializer


class BookingSerializer(serializers.ModelSerializer):
    """Serializer matching the precise Booking model schema."""

    customer_detail = CustomerPublicSerializer(source="customer", read_only=True)
    artisan_detail = ArtisanPublicSerializer(source="artisan", read_only=True)
    service_detail = ServiceSerializer(source="service", read_only=True)

    awaiting_customer_confirmation = serializers.SerializerMethodField()

    JOB_LOCATION_FIELDS = ("job_address", "job_latitude", "job_longitude")

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
            "finalization_method",
            "awaiting_customer_confirmation",
            "dispute_reason",
            "disputed_at",
        ]

        read_only_fields = fields

    def _can_view_job_location(self, booking):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user is None or not user.is_authenticated:
            return False

        if user.role == user.Role.ADMIN:
            return True

        if booking.customer_id and booking.customer.user_id == user.id:
            return True

        return (
            booking.artisan_id is not None
            and booking.artisan.user_id == user.id
            and booking.status in self.ARTISAN_LOCATION_VISIBLE_STATUSES
        )

    def to_representation(self, booking):
        data = super().to_representation(booking)

        if not self._can_view_job_location(booking):
            for field in self.JOB_LOCATION_FIELDS:
                data[field] = None

        return data

    def get_awaiting_customer_confirmation(self, booking):
        return booking.status == Booking.Status.COMPLETED


class BookingCreateSerializer(serializers.ModelSerializer):
    artisan = serializers.PrimaryKeyRelatedField(
        queryset=Artisan.objects.all(),
    )
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
    )
    # The artisan can't travel to a job without these.
    job_address = serializers.CharField(max_length=255)
    job_latitude = CoordinateField(min_value=-90, max_value=90)
    job_longitude = CoordinateField(min_value=-180, max_value=180)

    class Meta:
        model = Booking
        fields = [
            "artisan",
            "service",
            "job_address",
            "job_latitude",
            "job_longitude",
        ]


class BookingSummarySerializer(serializers.ModelSerializer):
    """Minimal booking info for places visible beyond the two parties
    (e.g. reviews). Never includes the job location."""

    service_detail = ServiceSerializer(source="service", read_only=True)

    class Meta:
        model = Booking
        # No status: whether a job was disputed stays between the two
        # parties and admins.
        fields = [
            "id",
            "service_detail",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
