from django.urls import path
from .views import SavedLocationListCreateView, SavedLocationDetailView

urlpatterns = [
    path("saved/locations", SavedLocationListCreateView.as_view(), name="saved-location-list-create"),
    path("saved/details/<int:pk>", SavedLocationDetailView.as_view(), name="saved-location-detail"),
]
# /api/v1/locations/saved/locations
# /api/v1/locations/saved/details/<int:pk>