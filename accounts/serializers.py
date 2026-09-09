from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from services.models import Service
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
        max_length=20
    )

    services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Service.objects.all(),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "full_name",
            "password",
            "phone_number",
            "services",
        ]

    def validate_services(self, services):
        if len(services) > 3:
            raise serializers.ValidationError(
                "An artisan can select a maximum of 3 services."
            )

        if len(services) < 1:
            raise serializers.ValidationError(
                "An artisan must select at least 1 service."
            )

        return services

    def create(self, validated_data):
        from .services import register_artisan
        return register_artisan(validated_data)
    
    
class CustomLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        # Authenticate user
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")

        # Generate JWT tokens manually
        refresh = RefreshToken.for_user(user)

        return {
            'username': user.username,
            'email': user.email,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
