from rest_framework.permissions import BasePermission


class IsBookingCustomer(BasePermission):
    def has_object_permission(self, request, view, booking):
        return (
            booking.customer_id is not None
            and booking.customer.user_id == request.user.id
        )


class IsBookingArtisan(BasePermission):
    def has_object_permission(self, request, view, booking):
        return (
            booking.artisan_id is not None
            and booking.artisan.user_id == request.user.id
        )
