from rest_framework import serializers

from accounts.serializers import UserPublicSerializer, UserSerializer
from locations.serializers import CoordinateField
from services.models import Service
from services.serializers import ServiceSerializer
from .models import Artisan, ServiceChangeRequest, ServiceQualificationEvidence


class ArtisanSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Artisan
        fields = [
            "id",
            "user",
            "phone_number",
            "business_name",
            "verification_status",
            "starting_price",
            "maximum_price",
            "default_location",
            "latitude",
            "longitude",
            "services",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "starting_price",
            "maximum_price",
            "services",
            "created_at",
            "updated_at",
        ]


class ArtisanPublicSerializer(serializers.ModelSerializer):
    """Artisan representation for other users (marketplace listing, nested
    booking detail). Excludes phone_number and email so customers and
    artisans can never reach each other outside the app."""

    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Artisan
        fields = [
            "id",
            "user",
            "business_name",
            "verification_status",
            "starting_price",
            "maximum_price",
            "default_location",
            "services",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ArtisanProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Artisan
        fields = [
            "id",
            "user",
            "phone_number",
            "business_name",
            "verification_status",
            "starting_price",
            "maximum_price",
            "default_location",
            "latitude",
            "longitude",
            "services",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "starting_price",
            "maximum_price",
            "services",
            "created_at",
            "updated_at",
        ]


class ServiceChangeRequestCreateSerializer(serializers.Serializer):
    services = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        many=True,
        required=True,
    )
    reason = serializers.CharField(
        required=True, allow_blank=False, trim_whitespace=True)
    trade_certificate = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        required=False,
    )
    training_completion = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        required=False,
    )
    portfolio_experience = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        required=False,
    )

    def validate(self, attrs):
        if "artisan" in self.initial_data or "artisan_id" in self.initial_data:
            raise serializers.ValidationError(
                "The artisan is determined from the authenticated account."
            )
        evidence_categories = {
            "trade_certificate",
            "training_completion",
            "portfolio_experience",
        }
        if len(evidence_categories.intersection(attrs)) < 2:
            raise serializers.ValidationError(
                "Upload evidence from at least two qualification categories."
            )
        return attrs

    def create(self, validated_data):
        from .services import create_service_change_request

        artisan = self.context["artisan"]
        service_ids = [service.id for service in validated_data["services"]]
        qualification_evidence = {
            category: validated_data[category]
            for category in (
                "trade_certificate",
                "training_completion",
                "portfolio_experience",
            )
            if category in validated_data
        }
        return create_service_change_request(
            artisan=artisan,
            service_ids=service_ids,
            reason=validated_data["reason"],
            qualification_evidence=qualification_evidence,
        )


class ServiceQualificationEvidenceSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceQualificationEvidence
        fields = ["id", "category", "uploaded_at", "download_url"]
        read_only_fields = fields

    def get_download_url(self, evidence):
        from django.urls import reverse

        return reverse(
            "service-change-request-evidence-download",
            kwargs={
                "pk": evidence.service_change_request_id,
                "evidence_id": evidence.id,
            },
        )


class ServiceChangeRequestSerializer(serializers.ModelSerializer):
    artisan = serializers.PrimaryKeyRelatedField(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    qualification_evidence = ServiceQualificationEvidenceSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = ServiceChangeRequest
        fields = [
            "id",
            "artisan",
            "services",
            "qualification_evidence",
            "reason",
            "status",
            "created_at",
            "reviewed_at",
        ]
        read_only_fields = fields


class ArtisanProfileUpdateSerializer(serializers.Serializer):

    full_name = serializers.CharField(
        required=False,
        max_length=150
    )

    profile_picture = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255
    )

    # Fields from the Artisan model
    business_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150
    )

    phone_number = serializers.CharField(
        required=False,
        max_length=20
    )

    default_location = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255
    )

    latitude = CoordinateField(
        required=False,
        allow_null=True,
        min_value=-90,
        max_value=90,
    )

    longitude = CoordinateField(
        required=False,
        allow_null=True,
        min_value=-180,
        max_value=180,
    )

    def validate(self, data):
        if ("latitude" in data) != ("longitude" in data):
            raise serializers.ValidationError(
                "Latitude and longitude must be updated together."
            )
        if "latitude" in data and (
            (data["latitude"] is None) != (data["longitude"] is None)
        ):
            raise serializers.ValidationError(
                "Latitude and longitude must both be set or both be cleared."
            )
        return data

    def update(self, instance, validated_data):
        from .services import update_artisan_profile

        return update_artisan_profile(
            instance,
            **validated_data
        )
