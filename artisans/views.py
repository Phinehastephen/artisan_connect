from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsArtisan
from .models import Artisan, ServiceChangeRequest, ServiceQualificationEvidence
from .serializers import (
    ArtisanProfileSerializer,
    ArtisanProfileUpdateSerializer,
    ArtisanPublicSerializer,
    ArtisanSerializer,
    ServiceChangeRequestCreateSerializer,
    ServiceChangeRequestSerializer,
)
from .services import (
    approve_artisan,
    approve_service_change_request,
    reject_artisan,
    reject_service_change_request,
    create_service_change_request,
)


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

        try:
            if action == "approve":
                artisan = approve_artisan(artisan)
                message = "Artisan approved successfully."
            else:
                artisan = reject_artisan(artisan)
                message = "Artisan rejected successfully."
        except ValidationError as e:
            return Response(
                {"detail": e.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

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


class ServiceChangeRequestListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.user.role == "ADMIN":
            requests = ServiceChangeRequest.objects.all().order_by("-created_at")
        elif request.user.role == "ARTISAN":
            requests = ServiceChangeRequest.objects.filter(
                artisan__user=request.user
            ).order_by("-created_at")
        else:
            return Response(
                {"error": "Only artisans or admins can view service change requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ServiceChangeRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if (
            request.user.role != "ARTISAN"
            or not hasattr(request.user, "artisan_profile")
        ):
            return Response(
                {"error": "Only artisans can submit service change requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ServiceChangeRequestCreateSerializer(
            data=request.data,
            context={"artisan": request.user.artisan_profile},
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            service_change_request = serializer.save()
        except ValidationError as exc:
            return Response({"error": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ServiceChangeRequestSerializer(service_change_request).data,
            status=status.HTTP_201_CREATED,
        )


class ServiceChangeRequestActionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, action, *args, **kwargs):
        try:
            service_change_request = ServiceChangeRequest.objects.get(pk=pk)
        except ServiceChangeRequest.DoesNotExist:
            return Response(
                {"error": "Service change request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if action not in ["approve", "reject"]:
            return Response(
                {"error": "Invalid action. Use 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if action == "approve":
                service_change_request = approve_service_change_request(
                    service_change_request
                )
                message = "Service change request approved successfully."
            else:
                service_change_request = reject_service_change_request(
                    service_change_request
                )
                message = "Service change request rejected successfully."
        except ValidationError as exc:
            return Response({"error": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": message,
                "service_change_request": ServiceChangeRequestSerializer(
                    service_change_request
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ServiceQualificationEvidenceDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, evidence_id, *args, **kwargs):
        evidence = ServiceQualificationEvidence.objects.select_related(
            "service_change_request__artisan__user"
        ).filter(
            pk=evidence_id,
            service_change_request_id=pk,
        ).first()
        if evidence is None:
            return Response(
                {"error": "Qualification evidence not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_admin = request.user.role == "ADMIN"
        is_owner = evidence.service_change_request.artisan.user_id == request.user.id
        if not (is_admin or is_owner):
            return Response(
                {"error": "Qualification evidence not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        filename = evidence.file.name.rsplit("/", 1)[-1]
        response = FileResponse(
            evidence.file.storage.open(evidence.file.name, "rb"),
            as_attachment=True,
            filename=filename,
            content_type="application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


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
