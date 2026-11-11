from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_alter_notification_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("BOOKING_REQUESTED", "Booking requested"),
                    ("BOOKING_ACCEPTED", "Booking accepted"),
                    ("BOOKING_REJECTED", "Booking rejected"),
                    ("BOOKING_CANCELLED", "Booking cancelled"),
                    ("BOOKING_ON_THE_WAY", "Artisan on the way"),
                    ("BOOKING_STARTED", "Work started"),
                    ("BOOKING_COMPLETED", "Work completed"),
                    (
                        "BOOKING_CONFIRMATION_REMINDER",
                        "Completion reminder",
                    ),
                    ("BOOKING_DISPUTED", "Booking disputed"),
                    ("BOOKING_FINALIZED", "Booking finalized"),
                    ("BOOKING_REOPENED", "Booking reopened"),
                    ("REVIEW_RECEIVED", "Review received"),
                    ("SERVICE_CHANGE_REQUESTED", "Service change requested"),
                    ("SERVICE_CHANGE_APPROVED", "Service change approved"),
                    ("SERVICE_CHANGE_REJECTED", "Service change rejected"),
                ],
                max_length=32,
            ),
        ),
    ]
