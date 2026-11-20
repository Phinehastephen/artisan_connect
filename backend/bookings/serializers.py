from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from .models import Booking
from services.models import ServiceScopeQuestion
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
    has_review = serializers.SerializerMethodField()
    scope_answers = serializers.SerializerMethodField()
    workflow_status = serializers.SerializerMethodField()
    artisan_on_the_way_at = serializers.SerializerMethodField()

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
            "workflow_status",
            "created_at",
            "updated_at",
            "accepted_at",
            "completed_at",
            "finalized_at",
            "finalization_method",
            "awaiting_customer_confirmation",
            "has_review",
            "dispute_reason",
            "disputed_at",
            "scope_answers",
            "artisan_on_the_way_at",
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

    def get_has_review(self, booking):
        try:
            booking.review
        except ObjectDoesNotExist:
            return False
        return True

    def get_scope_answers(self, booking):
        try:
            return booking.scope.answers
        except ObjectDoesNotExist:
            return []

    def get_workflow_status(self, booking):
        if booking.status == Booking.Status.ACCEPTED and self.get_artisan_on_the_way_at(booking):
            return "ON_THE_WAY"
        return booking.status

    def get_artisan_on_the_way_at(self, booking):
        try:
            return booking.journey.on_the_way_at
        except ObjectDoesNotExist:
            return None


class BookingCreateSerializer(serializers.ModelSerializer):
    JOB_LOCATION_TYPES = (
        ("saved", "Saved location"),
        ("current", "Current location"),
        ("custom", "Custom address"),
    )

    job_location_type = serializers.ChoiceField(
        choices=JOB_LOCATION_TYPES
    )

    job_location_id = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    artisan = serializers.PrimaryKeyRelatedField(
        queryset=Artisan.objects.all(),
    )

    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
    )

    job_address = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=255,
    )

    job_latitude = CoordinateField(
        required=False,
        min_value=-90,
        max_value=90,
    )

    job_longitude = CoordinateField(
        required=False,
        min_value=-180,
        max_value=180,
    )

    scope_answers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Booking
        fields = [
            "artisan",
            "service",
            "job_location_type",
            "job_location_id",
            "job_address",
            "job_latitude",
            "job_longitude",
            "scope_answers",
        ]

    def validate_scope_answers(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Provide scope answers as a list.")
        return value

    def _validate_scope_answers(self, attrs):
        service = attrs["service"]
        questions = list(
            ServiceScopeQuestion.objects.filter(
                service=service,
                is_active=True,
            ).prefetch_related("options")
        )
        supplied_answers = attrs.get("scope_answers", [])

        if not questions:
            if supplied_answers:
                raise serializers.ValidationError({
                    "scope_answers": "This service does not require scope answers."
                })
            attrs["_scope_snapshot"] = []
            return

        answers_by_question = {}
        for answer in supplied_answers:
            if not isinstance(answer, dict):
                raise serializers.ValidationError({
                    "scope_answers": "Each answer must include question and option IDs."
                })
            question_id = answer.get("question")
            option_id = answer.get("option")
            if (
                not isinstance(question_id, int)
                or isinstance(question_id, bool)
                or not isinstance(option_id, int)
                or isinstance(option_id, bool)
            ):
                raise serializers.ValidationError({
                    "scope_answers": "Each answer must include integer question and option IDs."
                })
            if question_id in answers_by_question:
                raise serializers.ValidationError({
                    "scope_answers": "A scope question may only be answered once."
                })
            answers_by_question[question_id] = option_id

        if set(answers_by_question) != {question.id for question in questions}:
            raise serializers.ValidationError({
                "scope_answers": "Answer every required question for this service."
            })

        snapshot = []
        for question in questions:
            option_id = answers_by_question[question.id]
            option = next(
                (
                    candidate
                    for candidate in question.options.all()
                    if candidate.id == option_id and candidate.is_active
                ),
                None,
            )
            if option is None:
                raise serializers.ValidationError({
                    "scope_answers": (
                        f"Choose a valid option for '{question.label}'."
                    )
                })
            snapshot.append({
                "key": question.key,
                "question": question.label,
                "value": option.value,
                "answer": option.label,
            })

        attrs["_scope_snapshot"] = snapshot

    def validate(self, attrs):
        location_type = attrs["job_location_type"]

        location_id = attrs.get("job_location_id")
        address = attrs.get("job_address")
        latitude = attrs.get("job_latitude")
        longitude = attrs.get("job_longitude")

        if location_type == "saved":
            if location_id is None:
                raise serializers.ValidationError({
                    "job_location_id": (
                        "Select a saved location."
                    )
                })

            if address is not None or latitude is not None or longitude is not None:
                raise serializers.ValidationError(
                    "For a saved location, submit only "
                    "job_location_type and job_location_id."
                )

        elif location_type == "current":
            if latitude is None or longitude is None:
                raise serializers.ValidationError({
                    "job_latitude": (
                        "Current location requires latitude "
                        "and longitude."
                    ),
                    "job_longitude": (
                        "Current location requires latitude "
                        "and longitude."
                    ),
                })

            if location_id is not None or address is not None:
                raise serializers.ValidationError(
                    "For current location, submit coordinates "
                    "without a saved location ID or address."
                )

        elif location_type == "custom":
            if not address or latitude is None or longitude is None:
                raise serializers.ValidationError(
                    "A custom location requires an address, "
                    "latitude, and longitude."
                )

            if location_id is not None:
                raise serializers.ValidationError(
                    "A custom location must not include "
                    "a saved location ID."
                )

        self._validate_scope_answers(attrs)
        return attrs

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
