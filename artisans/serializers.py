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
            "created_at",
            "updated_at",
        ]