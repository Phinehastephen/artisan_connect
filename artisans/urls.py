from django.urls import path

from .views import ArtisanListView


urlpatterns = [
    path("", ArtisanListView.as_view(), name="artisan-list"),
]