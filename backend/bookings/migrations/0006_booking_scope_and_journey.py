from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0005_booking_dispute_reason_booking_disputed_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookingScope",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("answers", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "booking",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scope",
                        to="bookings.booking",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BookingJourney",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("on_the_way_at", models.DateTimeField()),
                (
                    "booking",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="journey",
                        to="bookings.booking",
                    ),
                ),
            ],
        ),
    ]
