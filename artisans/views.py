from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Artisan
from .serializers import ArtisanSerializer
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdmin
from .services import approve_artisan, reject_artisan
# from .serializers import CustomLoginSerializer


class ArtisanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status="VERIFIED"
        ).order_by("-created_at")
        serializer = ArtisanSerializer(artisans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class ArtisanVerificationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, action):
        try:
            artisan = Artisan.objects.get(pk=pk)
        except Artisan.DoesNotExist:
            return Response(
                {"detail": "Artisan not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if action not in ["approve", "reject"]:
            return Response(
                {"detail": "Invalid action. Use 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only pending artisans can be approved or rejected
        if artisan.verification_status != Artisan.VerificationStatus.PENDING:
            return Response(
                {
                    "detail": (
                        "Only pending artisans can be approved or rejected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
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
            status=status.HTTP_200_OK
        )
        

class PendingArtisanListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.PENDING
        ).order_by("-created_at")

        serializer = ArtisanSerializer(artisans, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class RejectedArtisanListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.REJECTED
        ).order_by("-created_at")

        serializer = ArtisanSerializer(artisans, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )