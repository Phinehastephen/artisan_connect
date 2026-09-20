from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ValidationError

from accounts.permissions import IsAdmin
from .models import Service
from .serializers import ServiceSerializer
from .services import create_service,  update_service


class ServiceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = ServiceSerializer(
            services,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"detail": "Only admins can create services."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ServiceSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = create_service(
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description"),
                minimum_price=serializer.validated_data["minimum_price"],
                maximum_price=serializer.validated_data["maximum_price"],
                is_active=serializer.validated_data.get(
                    "is_active",
                    True
                ),
            )
        except Exception as error:
            return Response(
                {"detail": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            ServiceSerializer(service).data,
            status=status.HTTP_201_CREATED
        )
        
        
class ServiceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            service = Service.objects.get(pk=pk)
        except Service.DoesNotExist:
            return Response(
                {"detail": "Service not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Non-admin users can only view active services
        if (
            service.is_active is False
            and not IsAdmin().has_permission(request, self)
        ):
            return Response(
                {"detail": "Service not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ServiceSerializer(service)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        # Only admins can update services
        if not IsAdmin().has_permission(request, self):
            return Response(
                {"detail": "Only admins can update services."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = Service.objects.get(pk=pk)
        except Service.DoesNotExist:
            return Response(
                {"detail": "Service not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ServiceSerializer(
            service,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_service = update_service(
                service=service,
                name=serializer.validated_data.get("name"),
                description=serializer.validated_data.get("description"),
                minimum_price=serializer.validated_data.get("minimum_price"),
                maximum_price=serializer.validated_data.get("maximum_price"),
                is_active=serializer.validated_data.get("is_active"),
            )
        except ValidationError as error:
            return Response(
                {"detail": error.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ServiceSerializer(updated_service).data,
            status=status.HTTP_200_OK,
        )