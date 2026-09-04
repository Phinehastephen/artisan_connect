from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "role",
            "email_verified",
            "profile_picture",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "role",
            "email_verified",
            "is_active",
            "created_at",
            "updated_at",
        ]


class CustomerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
    )
    
    phone_number = serializers.CharField(
        max_length=20,
        required=True,
    )    

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "full_name",
            "password",
            "phone_number"
        ]

    def create(self, validated_data):
        from .services import register_customer

        return register_customer(validated_data)


class ArtisanRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
    )
    
    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "full_name",
            "password",
            "phone_number"
        ]

    def create(self, validated_data):
        from .services import register_artisan

        return register_artisan(validated_data)