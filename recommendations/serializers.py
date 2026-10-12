from rest_framework import serializers

from artisans.serializers import ArtisanPublicSerializer


class RecommendationResultSerializer(serializers.Serializer):
    artisan = ArtisanPublicSerializer(read_only=True)
    artisan_id = serializers.IntegerField()
    rating = serializers.FloatField(allow_null=True)
    completed_jobs = serializers.IntegerField()
    distance_km = serializers.FloatField()
    average_response_minutes = serializers.FloatField(allow_null=True)
    scores = serializers.DictField()
    total_score = serializers.FloatField()