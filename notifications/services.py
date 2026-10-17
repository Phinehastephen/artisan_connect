from .models import Notification


def create_notification(*, recipient, notification_type, title, message, target_path=""):
    return Notification.objects.create(
        recipient=recipient,
        type=notification_type,
        title=title,
        message=message,
        target_path=target_path,
    )


def notify_admins(*, notification_type, title, message, target_path=""):
    from accounts.models import User

    recipient_ids = User.objects.filter(
        role=User.Role.ADMIN,
        is_active=True,
    ).values_list("id", flat=True)
    return Notification.objects.bulk_create([
        Notification(
            recipient_id=recipient_id,
            type=notification_type,
            title=title,
            message=message,
            target_path=target_path,
        )
        for recipient_id in recipient_ids
    ])
