from django.core.management.base import BaseCommand

from bookings.services import (
    auto_finalize_overdue_bookings,
    send_due_confirmation_reminders,
)


class Command(BaseCommand):
    help = (
        "Email reminders to customers who haven't confirmed a completed job, "
        "and auto-finalize bookings left unconfirmed for 3 days. "
        "Run hourly (Task Scheduler / cron)."
    )

    def handle(self, *args, **options):
        reminders = send_due_confirmation_reminders()
        finalized = auto_finalize_overdue_bookings()

        self.stdout.write(
            f"Sent {reminders} reminder(s); auto-finalized {finalized} booking(s)."
        )
