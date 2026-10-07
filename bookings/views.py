from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from accounts.permissions import IsAdmin, IsCustomer, IsArtisan
from .models import Booking
from .permissions import IsBookingCustomer, IsBookingArtisan
from .serializers import BookingCreateSerializer, BookingSerializer
from .services import (
    create_booking,
    accept_booking,
    start_booking,
    complete_booking,
    confirm_completion,
    dispute_completion,
    finalize_booking,
    reopen_booking,
    reject_booking,
    cancel_booking,
)


class BookingListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.role == User.Role.ADMIN:
            bookings = Booking.objects.all()
        elif user.role == User.Role.ARTISAN:
            bookings = Booking.objects.filter(artisan__user=user)
        else:
            bookings = Booking.objects.filter(customer__user=user)

        bookings = bookings.order_by("-created_at")
        serializer = BookingSerializer(
            bookings, many=True, context={"request": request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class BookCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                booking = create_booking(
                    customer=request.user.customer_profile,
                    artisan=serializer.validated_data["artisan"],
                    service=serializer.validated_data["service"],
                    job_address=serializer.validated_data.get("job_address"),
                    job_latitude=serializer.validated_data.get("job_latitude"),
                    job_longitude=serializer.validated_data.get("job_longitude"),
                )

                return Response(
                    BookingSerializer(
                        booking, context={"request": request}
                    ).data,
                    status=status.HTTP_201_CREATED
                )

            except ValidationError as e:
                return Response(
                    {"error": e.messages},
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

        is_party_to_booking = (
            IsBookingCustomer().has_object_permission(request, self, booking)
            or IsBookingArtisan().has_object_permission(request, self, booking)
        )

        if request.user.role != User.Role.ADMIN and not is_party_to_booking:
            return Response(
                {"error": "You do not have permission to view this booking."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BookingSerializer(booking, context={"request": request})

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class BookingStatusActionView(APIView):
    permission_classes = [IsAuthenticated]

    ARTISAN_ACTIONS = {"accept", "start", "complete", "reject"}
    CUSTOMER_ACTIONS = {"cancel", "confirm", "disagree"}
    # Normally a booking finalizes when the customer confirms (or after 3
    # days); admins settle disputes by finalizing or reopening the job.
    ADMIN_ACTIONS = {"finalize", "reopen"}

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
            "confirm": confirm_completion,
            "disagree": lambda b: dispute_completion(
                b, request.data.get("reason")
            ),
            "finalize": finalize_booking,
            "reopen": reopen_booking,
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

        if action in self.ADMIN_ACTIONS and not IsAdmin().has_permission(request, self):
            return Response(
                {"error": "Only an admin can perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            updated_booking = action_map[action](booking)

            return Response(
                BookingSerializer(
                    updated_booking, context={"request": request}
                ).data,
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )