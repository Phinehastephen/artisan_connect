from django.urls import path

from .views import (
    BookingListAPIView,
    BookCreateAPIView,
    BookingDetailView,
    BookingStatusActionView,
)

urlpatterns = [
    path(
        "list",
        BookingListAPIView.as_view(),
        name="booking-list",
    ),
    # api/v1/bookings/list

    path(
        "booking/create",
        BookCreateAPIView.as_view(),
        name="booking-create",
    ),
    # api/v1/bookings/booking/create

    path(
        "details/<int:pk>",
        BookingDetailView.as_view(),
        name="booking-detail",
    ),
    # api/v1/bookings/details/<int:pk>
        
    path(
        "status/<int:pk>/<str:action>",
        BookingStatusActionView.as_view(),
        name="booking-status-action",
    ),
    # api/v1/bookings/status/<int:pk>/<str:action>
    
]