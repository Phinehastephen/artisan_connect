from django.shortcuts import render
from rest_framework import generics
from .models import Customer
from .serializers import CustomerSerializer

class CustomerDetailView(generics.RetrieveAPIView):
    serializer_class = CustomerSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return Customer.objects.all()
