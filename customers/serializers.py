from rest_framework import serializers
from accounts.serializers import UserSerializer
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "user",
            "phone_number",
            "created_at",
            "default_location",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

