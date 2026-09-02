from django.urls import path

from .views import ServiceListView


urlpatterns = [
    path("service", ServiceListView.as_view(), name="service-list"),
]

# api/v1/services/service