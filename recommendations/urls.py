from django.urls import path

from .views import RecommendationListAPIView

urlpatterns = [
    path(
        "rankings",
        RecommendationListAPIView.as_view(),
        name="recommendation-list",
    ),
]

# api/v1/recommendations/rankings