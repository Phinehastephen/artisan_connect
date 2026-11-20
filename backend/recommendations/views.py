from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from accounts.permissions import IsCustomer
from services.models import Service
from .services import rank_artisans
from .serializers import RecommendationResultSerializer


class RecommendationListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        service_id = request.query_params.get("service_id")
        latitude = request.query_params.get("latitude")
        longitude = request.query_params.get("longitude")

        if not service_id or not latitude or not longitude:
            raise ValidationError(
                "service_id, latitude, and longitude are required."
            )

        try:
            service_id = int(service_id)
        except (TypeError, ValueError):
            raise ValidationError("service_id must be a whole number.")

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise ValidationError(
                "Latitude and longitude must be valid numbers."
            )

        if not -90 <= latitude <= 90:
            raise ValidationError("Latitude must be between -90 and 90.")

        if not -180 <= longitude <= 180:
            raise ValidationError("Longitude must be between -180 and 180.")

        # Moved down here so auth/validation checks happen first
        service = get_object_or_404(
            Service,
            pk=service_id,
            is_active=True,
        )

        results = rank_artisans(
            latitude=latitude,
            longitude=longitude,
            service_id=service.id,
        )

        data = RecommendationResultSerializer(
            results,
            many=True,
        ).data

        return Response(data, status=status.HTTP_200_OK)