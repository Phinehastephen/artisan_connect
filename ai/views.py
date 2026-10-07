from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from accounts.permissions import IsCustomer
from locations.models import SavedLocation
from locations.serializers import NearbyArtisanMarkerSerializer
from locations.services import find_nearby_artisans, resolve_search_coordinates
from services.models import Service

from .models import SearchLog
from .serializers import ServiceBriefSerializer, SmartSearchQuerySerializer
from .services import log_search, match_service


CLARIFY_MESSAGE = (
    "We couldn't identify what you need. Please clarify, or choose a service below."
)
UNSURE_MESSAGE = "We're not sure what you need. Did you mean one of these?"


class SmartSearchView(APIView):
    # Query -> Smart Search -> service -> customer location -> 10 km ->
    # verified artisans offering it -> ranking.
    permission_classes = [IsAuthenticated, IsCustomer]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "smart_search"

    def get(self, request):
        query = SmartSearchQuerySerializer(data=request.query_params)

        if not query.is_valid():
            return Response(query.errors, status=status.HTTP_400_BAD_REQUEST)

        data = query.validated_data

        try:
            latitude, longitude = resolve_search_coordinates(
                user=request.user,
                location_type=data["location_type"],
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                location_id=data.get("location_id"),
            )
        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        result = match_service(data["q"])
        log_search(request.user.customer_profile, data["q"], result)

        response = {
            "query": data["q"],
            "confidence": result.confidence.lower(),
        }

        if result.confidence == SearchLog.Confidence.CONFIDENT:
            nearby = find_nearby_artisans(latitude, longitude, service=result.service)
            if nearby:
                message = f"Showing {result.service.name} artisans near you."
            else:
                message = f"No {result.service.name} artisans found within your area."
            response.update({
                "message": message,
                "service": ServiceBriefSerializer(result.service).data,
                "origin": {"latitude": float(latitude), "longitude": float(longitude)},
                "results": NearbyArtisanMarkerSerializer(nearby, many=True).data,
            })
        elif result.confidence == SearchLog.Confidence.UNSURE:
            response.update({
                "message": UNSURE_MESSAGE,
                "suggestions": ServiceBriefSerializer(result.suggestions, many=True).data,
            })
        else:
            response.update({
                "message": CLARIFY_MESSAGE,
                "services": ServiceBriefSerializer(
                    Service.objects.filter(is_active=True).order_by("name"),
                    many=True,
                ).data,
            })

        return Response(response, status=status.HTTP_200_OK)
