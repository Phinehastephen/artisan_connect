from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Service
from .serializers import ServiceSerializer


class ServiceListView(APIView):

    def get(self, request, *args, **kwargs):
        services = Service.objects.filter(is_active=True).order_by("name")
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)