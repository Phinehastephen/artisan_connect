from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from services.models import Service
from .models import User
from artisans.models import Artisan


def normalize_and_check_email(email):
    # Emails are stored lowercased so "John@Gmail.com" and "john@gmail.com"
    # can't become two separate accounts; the DB unique constraint alone is
    # case-sensitive.
    email = email.strip().lower()

    if User.objects.filter(email__iexact=email).exists():
        raise serializers.ValidationError(
            "An account with this email already exists."
        )

    return email



def check_username_available(username):
    # The DB constraint is case-sensitive; "TakenName" and "takenname" must
    # not both exist (customers can also rename themselves - same rule).
    if User.objects.filter(username__iexact=username).exists():
        raise serializers.ValidationError("This username is already taken.")
    return username


def validate_registration_password(data):
    # Run with a draft user so UserAttributeSimilarityValidator can reject
    # e.g. a password equal to the username - the same rules as reset.
    draft = User(
        username=data.get("username", ""),
        email=data.get("email", ""),
        full_name=data.get("full_name", ""),
    )
    try:
        validate_password(data["password"], user=draft)
    except DjangoValidationError as e:
        raise serializers.ValidationError({"password": e.messages})


def run_registration(register, validated_data):
    try:
        return register(validated_data)
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages)


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


class UserPublicSerializer(serializers.ModelSerializer):
    """User representation for the *other* party (nested in the customer/
    artisan public serializers). Excludes email, like phone_number, so
    customers and artisans can't contact each other outside the app."""

    class Meta:
        model = User
        # No username either: it's half of someone's login details and could
        # help find them on other platforms.
        fields = [
            "id",
            "full_name",
            "role",
            "profile_picture",
        ]
        read_only_fields = fields


class CustomerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
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

    def validate_email(self, email):
        return normalize_and_check_email(email)

    def validate_username(self, username):
        return check_username_available(username)

    def validate(self, data):
        validate_registration_password(data)
        return data

    def create(self, validated_data):
        from .services import register_customer

        return run_registration(register_customer, validated_data)


class ArtisanRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    phone_number = serializers.CharField(
        max_length=20
    )

    services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Service.objects.filter(is_active=True),
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

    def validate_email(self, email):
        return normalize_and_check_email(email)

    def validate_username(self, username):
        return check_username_available(username)

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

    def validate(self, data):
        validate_registration_password(data)
        return data

    def create(self, validated_data):
        from .services import register_artisan
        return run_registration(register_artisan, validated_data)
    
    
class CustomLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        # Authenticate user
        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError(
                "Invalid username or password."
            )

        if user.role == user.Role.ARTISAN:
            artisan = getattr(user, "artisan_profile", None)

            if artisan is None:
                raise serializers.ValidationError(
                    "This account isn't set up correctly. "
                    "Please contact the administrator."
                )

            if artisan.verification_status == Artisan.VerificationStatus.PENDING:
                raise serializers.ValidationError(
                    "Your artisan account is currently under review. "
                    "You will be able to log in once your account has been approved."
                )

            if artisan.verification_status == Artisan.VerificationStatus.REJECTED:
                raise serializers.ValidationError(
                    "Your artisan account has been rejected. "
                    "Please contact the administrator for more information."
                )

        refresh = RefreshToken.for_user(user)

        return {
            'username': user.username,
            'email': user.email,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={"invalid": "Enter the 6-digit code sent to your email."},
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        return data
