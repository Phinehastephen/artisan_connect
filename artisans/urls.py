from django.urls import path

from .views import (
    ArtisanListView,
    ArtisanVerificationAPIView,
    PendingArtisanListAPIView,
    RejectedArtisanListAPIView,
    ServiceChangeRequestListCreateAPIView,
    ServiceChangeRequestActionAPIView,
    ServiceQualificationEvidenceDownloadAPIView,
    ArtisanMyProfileView,
)


urlpatterns = [
    path("artisan", ArtisanListView.as_view(), name="artisan-list"),

    path("verification/<int:pk>/<str:action>",
         ArtisanVerificationAPIView.as_view(), name="artisan-verification"),

    path("pending", PendingArtisanListAPIView.as_view(), name="pending-artisans"),

    path("rejected", RejectedArtisanListAPIView.as_view(),
         name="rejected-artisans"),

    path("service-change-requests", ServiceChangeRequestListCreateAPIView.as_view(),
         name="service-change-request-list-create"),

    path("service-change-requests/<int:pk>/<str:action>",
         ServiceChangeRequestActionAPIView.as_view(), name="service-change-request-action"),
    path("service-change-requests/<int:pk>/evidence/<int:evidence_id>",
         ServiceQualificationEvidenceDownloadAPIView.as_view(), name="service-change-request-evidence-download"),

    path("me", ArtisanMyProfileView.as_view(), name="artisan-my-profile"),
]

# api/v1/artisans/artisan
# api/v1/artisans/verification/<int:pk>/<str:action>
# api/v1/artisans/pending
# api/v1/artisans/rejected
# api/v1/artisans/service-change-requests
# api/v1/artisans/service-change-requests/<int:pk>/<str:action>
# api/v1/artisans/service-change-requests/<int:pk>/evidence/<int:evidence_id>
# api/v1/artisans/me (patch/Get)
