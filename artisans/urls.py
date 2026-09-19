from django.urls import path

from .views import (
    ArtisanListView,
    ArtisanVerificationAPIView,
    PendingArtisanListAPIView,
    RejectedArtisanListAPIView,
    ArtisanMyProfileView,
)


urlpatterns = [
    path("artisan", ArtisanListView.as_view(), name="artisan-list"),
    path("verification/<int:pk>/<str:action>", ArtisanVerificationAPIView.as_view(), name="artisan-verification"),
    path("pending", PendingArtisanListAPIView.as_view(), name="pending-artisans"),
    path("rejected", RejectedArtisanListAPIView.as_view(), name="rejected-artisans"),
    path("me", ArtisanMyProfileView.as_view(), name="artisan-my-profile"),
]

# api/v1/artisans/artisan
# api/v1/artisans/verification
# api/v1/artisans/pending
# api/v1/artisans/rejected
# api/v1/artisans/me