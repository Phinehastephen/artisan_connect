from rest_framework import serializers

from locations.serializers import NearbyArtisanQuerySerializer
from services.models import Service


class SmartSearchQuerySerializer(NearbyArtisanQuerySerializer):
    q = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
    service = None


class ServiceBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name"]
