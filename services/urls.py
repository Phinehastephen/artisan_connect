from django.urls import path

from .views import ServiceListCreateAPIView


urlpatterns = [
    path("service", ServiceListCreateAPIView.as_view(), name="service-list"),
]

# api/v1/services/service