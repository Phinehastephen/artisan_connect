from django.urls import path

from .views import ServiceListCreateAPIView, ServiceDetailAPIView


urlpatterns = [
    path("service", ServiceListCreateAPIView.as_view(), name="service-list"),
    path("<int:pk>", ServiceDetailAPIView.as_view(), name="service-detail"),
]

# api/v1/services/service
# api/v1/services/<int:pk>