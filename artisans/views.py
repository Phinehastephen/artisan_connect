from django.shortcuts import render
from rest_framework import generics

from .models import Artisan
from .serializers import ArtisanSerializer


class ArtisanListView(generics.ListAPIView):
    serializer_class = ArtisanSerializer

    def get_queryset(self):
        return Artisan.objects.filter(
            verification_status="VERIFIED"
        ).order_by("-created_at")
