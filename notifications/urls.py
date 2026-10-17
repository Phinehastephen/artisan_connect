from django.urls import path

from .views import (
    NotificationListAPIView,
    NotificationMarkAllReadAPIView,
    NotificationMarkReadAPIView,
    NotificationUnreadCountAPIView,
)


urlpatterns = [
    path("list", NotificationListAPIView.as_view(), name="notification-list"),
    
    path("unread-count", NotificationUnreadCountAPIView.as_view(), name="notification-unread-count"),
    
    path("read-all", NotificationMarkAllReadAPIView.as_view(), name="notification-read-all"),
    
    path("<int:pk>/read", NotificationMarkReadAPIView.as_view(), name="notification-mark-read"),
]

# api/v1/notifications/list
# api/v1/notifications/unread-count
# api/v1/notifications/read-all
# api/v1/notifications/<int:pk>/read
