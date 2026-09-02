# from rest_framework import generics

# from .models import Artisan
# from .serializers import ArtisanSerializer


# class ArtisanListView(generics.ListAPIView):
#     serializer_class = ArtisanSerializer

#     def get_queryset(self):
#         return Artisan.objects.filter(
#             verification_status="VERIFIED"
#         ).order_by("-created_at")


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Artisan
from .serializers import ArtisanSerializer


class ArtisanListView(APIView):

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status="VERIFIED"
        ).order_by("-created_at")
        serializer = ArtisanSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)