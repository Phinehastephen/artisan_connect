import math

from rest_framework import serializers
from services.models import Service

from .models import SavedLocation
from .services import MAP_COORDINATE_DECIMALS


def finite(value):
    if not math.isfinite(value):
        raise serializers.ValidationError("A valid number is required.")


class CoordinateField(serializers.DecimalField):
    # Phone GPS often has 7+ decimal places; round to the stored 6 (~0.1 m)
    # instead of rejecting the request.
    def __init__(self, **kwargs):
        super().__init__(max_digits=9, decimal_places=6, **kwargs)

    def validate_precision(self, value):
        return value


class SavedLocationSerializer(serializers.ModelSerializer):
    """Serializer matching the exact SavedLocation model schema."""

    latitude = CoordinateField(min_value=-90, max_value=90)
    longitude = CoordinateField(min_value=-180, max_value=180)

    class Meta:
        model = SavedLocation
        fields = [
            "id",
            "customer",
            "name",
            "address",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id",
                            "customer",
                            "created_at",
                            "updated_at"]
        

class NearbyArtisanQuerySerializer(serializers.Serializer):
    
    
    LOCATION_TYPE_CURRENT = "current"
    LOCATION_TYPE_SAVED = "saved"

    location_type = serializers.ChoiceField(
        choices=[LOCATION_TYPE_CURRENT, LOCATION_TYPE_SAVED],
        default=LOCATION_TYPE_CURRENT,
    )
    latitude = serializers.FloatField(
        required=False,
        validators=[finite],
        min_value=-90,
        max_value=90,
        error_messages={
            "min_value": "Latitude must be between -90 and 90.",
            "max_value": "Latitude must be between -90 and 90.",
        },
    )
    longitude = serializers.FloatField(
        required=False,
        validators=[finite],
        min_value=-180,
        max_value=180,
        error_messages={
            "min_value": "Longitude must be between -180 and 180.",
            "max_value": "Longitude must be between -180 and 180.",
        },
    )
    location_id = serializers.IntegerField(required=False, min_value=1)
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
    )

    def validate(self, data):
        if data["location_type"] == self.LOCATION_TYPE_SAVED:
            if "location_id" not in data:
                raise serializers.ValidationError(
                    {"location_id": "location_id is required when location_type is 'saved'."}
                )
        elif "latitude" not in data or "longitude" not in data:
            raise serializers.ValidationError(
                "Both latitude and longitude are required."
            )

        return data


class NearbyArtisanMarkerSerializer(serializers.Serializer):

    id = serializers.IntegerField(source="artisan.id")
    name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    distance_km = serializers.FloatField()
    location = serializers.CharField(source="artisan.default_location", allow_null=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField(source="artisan.review_count")
    starting_price = serializers.DecimalField(
        source="artisan.starting_price", max_digits=12, decimal_places=2
    )
    maximum_price = serializers.DecimalField(
        source="artisan.maximum_price", max_digits=12, decimal_places=2
    )

    def get_name(self, item):
        artisan = item["artisan"]
        return artisan.business_name or artisan.user.full_name

    def get_is_verified(self, item):
        return item["artisan"].verification_status == "VERIFIED"

    def get_latitude(self, item):
        return round(float(item["artisan"].latitude), MAP_COORDINATE_DECIMALS)

    def get_longitude(self, item):
        return round(float(item["artisan"].longitude), MAP_COORDINATE_DECIMALS)

    def get_average_rating(self, item):
        rating = item["artisan"].average_rating
        return None if rating is None else round(float(rating), 1)


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=200, trim_whitespace=True)


class ReverseGeocodeQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90, validators=[finite])
    longitude = serializers.FloatField(min_value=-180, max_value=180, validators=[finite])
