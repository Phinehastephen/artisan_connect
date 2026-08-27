from rest_framework import serializers
from .models import SavedLocation


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
        read_only_fields = ["id", "created_at", "updated_at"]