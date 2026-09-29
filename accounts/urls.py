from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomJWTLoginView

from .views import (
    CustomerRegisterAPIView,
    ArtisanRegisterAPIView,
    VerifyEmailAPIView,
    ResendVerificationEmailAPIView,
    PasswordResetRequestAPIView,
    PasswordResetVerifyAPIView,
    PasswordResetConfirmAPIView,
)

urlpatterns = [
    path(
        "register/customer",
        CustomerRegisterAPIView.as_view(),
        name="customer-register"
    ),
    # api/v1/accounts/register/customer

    path(
        "register/artisan",
        ArtisanRegisterAPIView.as_view(),
        name="artisan-register"
    ),
    # api/v1/accounts/register/artisan
    
    path(
        'auth/login',
        CustomJWTLoginView.as_view(),
        name='auth_login'
        ),
     # api/v1/accounts/auth/login
    
    path(
        'auth/refresh',
        TokenRefreshView.as_view(),
        name='token_refresh'
        ),
     # api/v1/accounts/auth/refresh

    path(
        "verify-email/<str:token>",
        VerifyEmailAPIView.as_view(),
        name="verify-email",
    ),
    # api/v1/accounts/verify-email/<token>

    path(
        "resend-verification",
        ResendVerificationEmailAPIView.as_view(),
        name="resend-verification",
    ),
    # api/v1/accounts/resend-verification

    path(
        "password-reset/request",
        PasswordResetRequestAPIView.as_view(),
        name="password-reset-request",
    ),
    # api/v1/accounts/password-reset/request

    path(
        "password-reset/verify",
        PasswordResetVerifyAPIView.as_view(),
        name="password-reset-verify",
    ),
    # api/v1/accounts/password-reset/verify

    path(
        "password-reset/confirm",
        PasswordResetConfirmAPIView.as_view(),
        name="password-reset-confirm",
    ),
    # api/v1/accounts/password-reset/confirm
]