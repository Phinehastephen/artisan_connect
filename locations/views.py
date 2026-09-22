from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer

from .models import SavedLocation
from .serializers import SavedLocationSerializer
from .services import create_saved_location


class SavedLocationListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, *args, **kwargs):
        customer = request.user.customer_profile

        saved_locations = SavedLocation.objects.filter(
            customer=customer
        ).order_by("-id")

        serializer = SavedLocationSerializer(
            saved_locations,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        serializer = SavedLocationSerializer(data=request.data)

        if serializer.is_valid():
            customer = request.user.customer_profile

            try:
                saved_location = create_saved_location(
                    customer=customer,
                    name=serializer.validated_data["name"],
                    address=serializer.validated_data["address"],
                    latitude=serializer.validated_data["latitude"],
                    longitude=serializer.validated_data["longitude"],
                )

                return Response(
                    SavedLocationSerializer(saved_location).data,
                    status=status.HTTP_201_CREATED,
                )

            except ValidationError as e:
                return Response(
                    {"error": e.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class SavedLocationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request, pk, *args, **kwargs):
        try:
            saved_location = SavedLocation.objects.get(
                pk=pk,
                customer=request.user.customer_profile,
            )

        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SavedLocationSerializer(saved_location)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk, *args, **kwargs):
        try:
            saved_location = SavedLocation.objects.get(
                pk=pk,
                customer=request.user.customer_profile,
            )

        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        saved_location.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )