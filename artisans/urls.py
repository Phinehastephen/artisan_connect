from django.urls import path

from .views import ArtisanListView


urlpatterns = [
    path("artisan", ArtisanListView.as_view(), name="artisan-list"),
]

# api/v1/artisans/artisan