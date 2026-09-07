from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomJWTLoginView

from .views import (
    CustomerRegisterAPIView,
    ArtisanRegisterAPIView,
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
]