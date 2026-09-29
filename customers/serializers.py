from rest_framework import serializers
from accounts.serializers import UserPublicSerializer, UserSerializer
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


class CustomerPublicSerializer(serializers.ModelSerializer):
    """Customer representation for other users (nested booking detail).
    Excludes phone_number, email and default_location so artisans and
    customers can never reach each other outside the app."""

    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

