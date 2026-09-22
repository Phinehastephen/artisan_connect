from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsArtisan
from .models import Artisan
from .serializers import (
    ArtisanProfileSerializer,
    ArtisanProfileUpdateSerializer,
    ArtisanPublicSerializer,
    ArtisanSerializer,
)
from .services import approve_artisan, reject_artisan


class ArtisanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.VERIFIED
        ).order_by("-created_at")
        serializer = ArtisanPublicSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArtisanVerificationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, action):
        try:
            artisan = Artisan.objects.get(pk=pk)
        except Artisan.DoesNotExist:
            return Response(
                {"detail": "Artisan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if action not in ["approve", "reject"]:
            return Response(
                {"detail": "Invalid action. Use 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if artisan.verification_status != Artisan.VerificationStatus.PENDING:
            return Response(
                {"detail": "Only pending artisans can be approved or rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "approve":
            artisan = approve_artisan(artisan)
            message = "Artisan approved successfully."
        else:
            artisan = reject_artisan(artisan)
            message = "Artisan rejected successfully."

        return Response(
            {
                "message": message,
                "artisan": ArtisanSerializer(artisan).data,
            },
            status=status.HTTP_200_OK,
        )


class PendingArtisanListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.PENDING
        ).order_by("-created_at")

        serializer = ArtisanSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RejectedArtisanListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.REJECTED
        ).order_by("-created_at")

        serializer = ArtisanSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArtisanMyProfileView(APIView):
    permission_classes = [IsAuthenticated, IsArtisan]

    def get(self, request):
        try:
            artisan = request.user.artisan_profile
        except Artisan.DoesNotExist:
            return Response(
                {"detail": "Artisan profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ArtisanProfileSerializer(artisan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        try:
            artisan = request.user.artisan_profile
        except Artisan.DoesNotExist:
            return Response(
                {"detail": "Artisan profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ArtisanProfileUpdateSerializer(
            artisan,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            try:
                updated_artisan = serializer.save()
            except ValidationError as e:
                error_detail = e.messages if hasattr(e, "messages") else str(e)
                return Response(
                    {"error": error_detail},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                ArtisanProfileSerializer(updated_artisan).data,
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)