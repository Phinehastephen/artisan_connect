from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    UserSerializer,
    CustomerRegisterSerializer,
    ArtisanRegisterSerializer,
)


class CustomerRegisterAPIView(APIView):

    def post(self, request, *args, **kwargs):

        serializer = CustomerRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ArtisanRegisterAPIView(APIView):

    def post(self, request, *args, **kwargs):

        serializer = ArtisanRegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
        

# Create your views here.

# create a class based view (using APIView) with its HTTP methods
# logic will depend on the API view you need for example create user should take details from
# serializer and use django's create user methods to create the instance of that user
# When creation of details is successful then return Response

# call this API in the urls file and define its endpoint there
# Test and ensure it works
