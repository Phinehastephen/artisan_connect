from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from .models import Review
from .serializers import ReviewEditSerializer, ReviewSerializer
from .services import create_review, edit_review

from rest_framework.permissions import IsAuthenticated

class ReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated()]

    def get(self, request, *args, **kwargs):
        reviews = Review.objects.all().order_by("-created_at")
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                review = create_review(
                    booking=serializer.validated_data["booking"],
                    customer=request.user.customer_profile,
                    rating=serializer.validated_data["rating"],
                    comment=serializer.validated_data.get("comment", ""),
                )
                return Response(
                    ReviewSerializer(review).data,
                    status=status.HTTP_201_CREATED,
                )
            except ValidationError as e:
                return Response(
                    {"error": e.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated()]

    def get(self, request, pk, *args, **kwargs):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return Response(
                {"error": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk, *args, **kwargs):
        try:
            review = Review.objects.get(pk=pk)
        except Review.DoesNotExist:
            return Response(
                {"error": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReviewEditSerializer(data=request.data)
        if serializer.is_valid():
            try:
                updated_review = edit_review(
                    review=review,
                    customer=request.user.customer_profile,
                    rating=serializer.validated_data["rating"],
                    comment=serializer.validated_data.get("comment", review.comment),
                )
                return Response(
                    ReviewSerializer(updated_review).data,
                    status=status.HTTP_200_OK,
                )
            except ValidationError as e:
                return Response(
                    {"error": e.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)