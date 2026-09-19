from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer
from .serializers import CustomerSerializer
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