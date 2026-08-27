from django.urls import path
from .views import CustomerDetailView

urlpatterns = [
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]