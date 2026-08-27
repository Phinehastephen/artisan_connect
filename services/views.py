from django.shortcuts import render
from rest_framework import generics

from .models import Service
from .serializers import ServiceSerializer


class ServiceListView(generics.ListAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Service.objects.filter(
            is_active=True
        ).order_by("name")