from django.urls import path
from .views import (
    SavedLocationListCreateView, 
    SavedLocationDetailView, 
    NearbyArtisanListView,
    GeocodeView,
    ReverseGeocodeView,
    )

urlpatterns = [
    path("create/locations", SavedLocationListCreateView.as_view(), name="saved-location-list-create"),
    path("saved/details/<int:pk>", SavedLocationDetailView.as_view(), name="saved-location-detail"),
    path("nearby-artisans", NearbyArtisanListView.as_view(), name="nearby-artisan"),
    path("geocode", GeocodeView.as_view(), name="geocode"),
    path("reverse-geocode", ReverseGeocodeView.as_view(), name="reverse-geocode"),
]
# /api/v1/locations/create/locations
# /api/v1/locations/saved/details/<int:pk>
# /api/v1/locations/nearby-artisans
# /api/v1/locations/geocode?q=<address>
# /api/v1/locations/reverse-geocode?latitude=<lat>&longitude=<lon>