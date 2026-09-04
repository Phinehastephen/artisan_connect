from django.urls import path

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
]