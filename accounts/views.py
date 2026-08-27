from django.shortcuts import render

# Create your views here.

# create a class based view (using APIView) with its HTTP methods
# logic will depend on the API view you need for example create user should take details from
# serializer and use django's create user methods to create the instance of that user
# When creation of details is successful then return Response

# call this API in the urls file and define its endpoint there
# Test and ensure it works
