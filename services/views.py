from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from .models import Service
from .serializers import ServiceSerializer
from .services import create_service


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