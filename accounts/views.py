from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from .serializers import CustomLoginSerializer

from .serializers import (
    UserSerializer,
    CustomerRegisterSerializer,
    ArtisanRegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    PasswordResetConfirmSerializer,
)
from .services import (
    create_email_verification_token,
    send_verification_email,
    verify_email,
    request_password_reset,
    verify_password_reset_code,
    reset_password,
)


class CustomerRegisterAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"

    def post(self, request, *args, **kwargs):

        serializer = CustomerRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ArtisanRegisterAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration"
    
    def post(self, request, *args, **kwargs):

        serializer = ArtisanRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
class CustomJWTLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = CustomLoginSerializer(data=request.data)
        if serializer.is_valid():
            # Return tokens along with user info
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailAPIView(APIView):
    """
    Confirms account ownership of the registered email address. This is
    intentionally non-blocking: an unverified customer/artisan can still
    log in and use the app fully (see README's Email Verification section).
    """

    permission_classes = [AllowAny]

    def get(self, request, token, *args, **kwargs):
        try:
            user = verify_email(token)
        except ValidationError as e:
            error_detail = e.messages if hasattr(e, "messages") else str(e)
            return Response(
                {"error": error_detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Email verified successfully.",
                "email_verified": user.email_verified,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationEmailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification"

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.email_verified:
            return Response(
                {"detail": "This email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = create_email_verification_token(user)
        send_verification_email(user, token)

        return Response(
            {"detail": "Verification email sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestAPIView(APIView):
    """
    Step 1: email a 6-digit code. The response is identical whether or not
    the email is registered, so this can't be used to probe for accounts.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        request_password_reset(serializer.validated_data["email"])

        return Response(
            {
                "detail": "If an account exists for this email, "
                "a 6-digit reset code has been sent to it."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetVerifyAPIView(APIView):
    """
    Step 2: exchange the emailed code for a single-use reset_token that
    the client sends along with the new password in step 3.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_verify"

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetVerifySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_token = verify_password_reset_code(
                serializer.validated_data["email"],
                serializer.validated_data["code"],
            )
        except ValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Code verified. You can now set a new password.",
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmAPIView(APIView):
    """Step 3: set the new password using the reset_token from step 2."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            reset_password(
                serializer.validated_data["reset_token"],
                serializer.validated_data["new_password"],
            )
        except ValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Password reset successful. You can now log in."},
            status=status.HTTP_200_OK,
        )

