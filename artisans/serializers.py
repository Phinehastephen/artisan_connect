from rest_framework import serializers

from accounts.serializers import UserSerializer
from .models import Artisan


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
    booking detail). Excludes phone_number so customers and artisans can
    never reach each other outside the app."""

    user = UserSerializer(read_only=True)

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

    def update(self, instance, validated_data):
        from .services import update_artisan_profile

        return update_artisan_profile(
            instance,
            **validated_data
        )