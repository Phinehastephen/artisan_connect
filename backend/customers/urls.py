from django.urls import path
from .views import CustomerDetailView

urlpatterns = [
    path("customer/details", CustomerDetailView.as_view(), name="customer-detail"),
    #api/v1/customers/customer/details
    
    # base = config.urls
    # sub = customers.urls
    
    # base + sub
    # base = /api/v1/my/app
    # sub = register/user
    # full url = /api/v1/my/app/register/user
]