from rest_framework import serializers
from accounts.models import User
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


class CustomerProfileUpdateSerializer(serializers.Serializer):
    LOCKED_FIELDS = ("phone_number", "email")

    username = serializers.CharField(
        max_length=150,
        required=False,
        validators=User._meta.get_field("username").validators,
    )
    full_name = serializers.CharField(max_length=150, required=False)
    profile_picture = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    default_location = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, data):
        # Say so explicitly rather than silently ignoring them, so the app
        # doesn't think the change went through.
        locked = [name for name in self.LOCKED_FIELDS if name in self.initial_data]
        if locked:
            raise serializers.ValidationError(
                {name: "This can't be changed." for name in locked}
            )

        if not data:
            raise serializers.ValidationError("No changes were provided.")

        return data
