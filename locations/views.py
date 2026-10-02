from django.core.exceptions import ValidationError
from django.shortcuts import render
from .models import Location


from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from .services import (
    GeocodingUnavailable,
    find_nearby_artisans,
    geocode_address,
    resolve_search_coordinates,
    reverse_geocode,
)
from .serializers import (
    GeocodeQuerySerializer,
    NearbyArtisanQuerySerializer,
    NearbyArtisanMarkerSerializer,
    ReverseGeocodeQuerySerializer,
)

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
        

class NearbyArtisanListView(APIView):
    """
    GET /nearby-artisans?latitude=..&longitude=..           
    GET /nearby-artisans?location_type=saved&location_id=5
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = NearbyArtisanQuerySerializer(data=request.query_params)

        if not query.is_valid():
            return Response(
                query.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            latitude, longitude = resolve_search_coordinates(
                user=request.user,
                location_type=query.validated_data["location_type"],
                latitude=query.validated_data.get("latitude"),
                longitude=query.validated_data.get("longitude"),
                location_id=query.validated_data.get("location_id"),
            )
        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nearby_artisans = find_nearby_artisans(
            latitude,
            longitude,
        )

        markers = NearbyArtisanMarkerSerializer(
            nearby_artisans,
            many=True,
        )

        return Response(
            {

                "origin": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "results": markers.data,
            },
            status=status.HTTP_200_OK,
        )


def map_view(request):
    locations = Location.objects.all()
    return render(request, 'map.html', {'locations': locations})


class GeocodeView(APIView):
 

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "geocoding"

    def get(self, request):
        query = GeocodeQuerySerializer(data=request.query_params)

        if not query.is_valid():
            return Response(query.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = geocode_address(query.validated_data["q"])
        except GeocodingUnavailable as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(results, status=status.HTTP_200_OK)


class ReverseGeocodeView(APIView):
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "geocoding"

    def get(self, request):
        query = ReverseGeocodeQuerySerializer(data=request.query_params)

        if not query.is_valid():
            return Response(query.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            place = reverse_geocode(
                query.validated_data["latitude"],
                query.validated_data["longitude"],
            )
        except GeocodingUnavailable as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if place is None:
            return Response(
                {"error": "No address found for these coordinates."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(place, status=status.HTTP_200_OK)
