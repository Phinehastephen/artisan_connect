from rest_framework import serializers

from locations.serializers import (
    NearbyArtisanMarkerSerializer,
    NearbyArtisanQuerySerializer,
)
from services.models import Service


class SmartSearchQuerySerializer(NearbyArtisanQuerySerializer):
    q = serializers.CharField(
        min_length=2, max_length=200, trim_whitespace=True)
    service = None


class ServiceBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name"]


class SmartSearchRankedArtisanSerializer(NearbyArtisanMarkerSerializer):
    completed_jobs = serializers.IntegerField()
    average_response_minutes = serializers.FloatField(allow_null=True)
    scores = serializers.DictField()
    total_score = serializers.FloatField()
