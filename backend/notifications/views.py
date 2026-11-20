from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        )
        unread_only = request.query_params.get("unread_only", "false").lower()
        if unread_only in {"1", "true", "yes"}:
            notifications = notifications.filter(read_at__isnull=True)

        try:
            page = max(int(request.query_params.get("page", 1)), 1)
            page_size = min(
                max(int(request.query_params.get("page_size", 50)), 1), 100)
        except (TypeError, ValueError):
            return Response(
                {"error": "page and page_size must be positive integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_count = notifications.count()
        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
        start = (page - 1) * page_size
        results = notifications[start:start + page_size]

        return Response(
            {
                "count": total_count,
                "unread_count": unread_count,
                "page": page,
                "page_size": page_size,
                "results": NotificationSerializer(results, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class NotificationUnreadCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
        return Response({"unread_count": unread_count}, status=status.HTTP_200_OK)


class NotificationMarkReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = Notification.objects.filter(
            pk=pk,
            recipient=request.user,
        ).first()
        if notification is None:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response(
            {"updated_count": updated_count},
            status=status.HTTP_200_OK,
        )
