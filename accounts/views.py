from django.db.migrations import serializer
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError

from .models import User
from .serializers import UserSerializer


class AccountCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        
        serializer = UserSerializer(data=request.data)
        
        

# Create your views here.

# create a class based view (using APIView) with its HTTP methods
# logic will depend on the API view you need for example create user should take details from
# serializer and use django's create user methods to create the instance of that user
# When creation of details is successful then return Response

# call this API in the urls file and define its endpoint there
# Test and ensure it works
