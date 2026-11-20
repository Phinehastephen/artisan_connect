from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ValidationError

from .models import Customer
from .serializers import CustomerProfileUpdateSerializer, CustomerSerializer
from .services import update_customer_profile
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsCustomer


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        try:
            customer = request.user.customer_profile
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CustomerProfileUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = update_customer_profile(customer, serializer.validated_data)
        except ValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)
