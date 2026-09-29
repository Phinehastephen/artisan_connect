from rest_framework import serializers
from .models import SavedLocation
from artisans.serializers import ArtisanPublicSerializer


class SavedLocationSerializer(serializers.ModelSerializer):
    """Serializer matching the exact SavedLocation model schema."""

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
    """
    Query params for nearby-artisan search. Either search around the
    caller's current GPS position, or around one of their saved locations.
    Omitting location_type behaves as "current".
    """

    LOCATION_TYPE_CURRENT = "current"
    LOCATION_TYPE_SAVED = "saved"

    location_type = serializers.ChoiceField(
        choices=[LOCATION_TYPE_CURRENT, LOCATION_TYPE_SAVED],
        default=LOCATION_TYPE_CURRENT,
    )
    latitude = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
        error_messages={
            "min_value": "Latitude must be between -90 and 90.",
            "max_value": "Latitude must be between -90 and 90.",
        },
    )
    longitude = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
        error_messages={
            "min_value": "Longitude must be between -180 and 180.",
            "max_value": "Longitude must be between -180 and 180.",
        },
    )
    location_id = serializers.IntegerField(required=False, min_value=1)

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


class NearbyArtisanSerializer(serializers.Serializer):
    artisan = ArtisanPublicSerializer(read_only=True)
    distance_km = serializers.FloatField()