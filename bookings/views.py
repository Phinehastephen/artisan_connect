from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from .models import Booking
from .serializers import BookingSerializer
from .services import (
    create_booking,
    accept_booking,
    start_booking,
    complete_booking,
    finalize_booking,
)


class BookingListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        bookings = Booking.objects.all().order_by("-created_at")
        serializer = BookingSerializer(bookings, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class BookCreateAPIView(APIView):
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
    """

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
        }

        if action not in action_map:
            return Response(
                {"error": f"Invalid action: '{action}'"},
                status=status.HTTP_400_BAD_REQUEST
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