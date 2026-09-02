from django.urls import path
from .views import SavedLocationListCreateView, SavedLocationDetailView

urlpatterns = [
    path("save/locations", SavedLocationListCreateView.as_view(), name="saved-location-list-create"),
    path("location/details/<int:pk>/", SavedLocationDetailView.as_view(), name="saved-location-detail"),
]
# /api/v1/locations/save/locations