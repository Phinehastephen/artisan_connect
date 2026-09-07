from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Artisan
from .serializers import ArtisanSerializer
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
# from .serializers import CustomLoginSerializer


class ArtisanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status="VERIFIED"
        ).order_by("-created_at")
        serializer = ArtisanSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
