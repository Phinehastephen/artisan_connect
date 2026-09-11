from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsCustomer, IsArtisan
from .models import Booking
from .permissions import IsBookingCustomer, IsBookingArtisan
from .serializers import BookingSerializer
from .services import (
    create_booking,
    accept_booking,
    start_booking,
    complete_booking,
    finalize_booking,
    reject_booking,
    cancel_booking,
)


class BookingListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        bookings = Booking.objects.all().order_by("-created_at")
        serializer = BookingSerializer(bookings, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class BookCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request, *args, **kwargs):
        serializer = BookingSerializer(data=request.data)

        if serializer.is_valid():
            try:
                booking = create_booking(
                    customer=serializer.validated_data.get("customer"),
                    artisan=serializer.validated_data.get("artisan"),
                    service=serializer.validated_data.get("service"),
                    job_address=serializer.validated_data.get("job_address"),
                    job_latitude=serializer.validated_data.get("job_latitude"),
                    job_longitude=serializer.validated_data.get("job_longitude"),
                )

                return Response(
                    BookingSerializer(booking).data,
                    status=status.HTTP_201_CREATED
                )

            except ValidationError as e:
                return Response(
                    {"error": e.message},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BookingSerializer(booking)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class BookingStatusActionView(APIView):
    """
    Handles state transitions for a booking based on the requested action.

    "finalize" is intentionally left open to any authenticated user involved
    in the booking's lifecycle rather than gated to a single role, since the
    project has not yet decided who is responsible for triggering it.
    """
    permission_classes = [IsAuthenticated]

    ARTISAN_ACTIONS = {"accept", "start", "complete", "reject"}
    CUSTOMER_ACTIONS = {"cancel"}

    def post(self, request, pk, action):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        action_map = {
            "accept": accept_booking,
            "start": start_booking,
            "complete": complete_booking,
            "finalize": finalize_booking,
            "reject": reject_booking,
            "cancel": cancel_booking,
        }

        if action not in action_map:
            return Response(
                {"error": f"Invalid action: '{action}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action in self.ARTISAN_ACTIONS and not (
            IsArtisan().has_permission(request, self)
            and IsBookingArtisan().has_object_permission(request, self, booking)
        ):
            return Response(
                {"error": "Only the artisan on this booking can perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        if action in self.CUSTOMER_ACTIONS and not (
            IsCustomer().has_permission(request, self)
            and IsBookingCustomer().has_object_permission(request, self, booking)
        ):
            return Response(
                {"error": "Only the customer on this booking can perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            updated_booking = action_map[action](booking)

            return Response(
                BookingSerializer(updated_booking).data,
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )