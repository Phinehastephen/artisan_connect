from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Artisan
from .serializers import ArtisanSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
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
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        # Checks if the logged-in user is an admin      
        all_artisans = Artisan.objects.all()
        for art in all_artisans:
            print(f"Artisan ID: {art.id}, Verification Status: {art.verification_status}")
        if request.user.role != "ADMIN":
            return Response(
                {"detail": "Only admins can approve or reject artisans."},
                status=status.HTTP_403_FORBIDDEN
            )

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
    permission_classes = [IsAuthenticated]  # Adjust permissions as needed

    def get(self, request):
        # Only admins can view pending artisans
        if request.user.role != "ADMIN":
            return Response(
                {"detail": "Only admins can view pending artisans."},
                status=status.HTTP_403_FORBIDDEN
            )

        artisans = Artisan.objects.filter(
            verification_status=Artisan.VerificationStatus.PENDING
        ).order_by("-created_at")

        serializer = ArtisanSerializer(artisans, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
