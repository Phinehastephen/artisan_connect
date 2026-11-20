from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from ai.models import SearchLog

SEARCH_LOG_RETENTION_MONTHS = 12


class Command(BaseCommand):
    help = "Delete search logs older than 12 months. Run daily."

    def handle(self, *args, **options):
        cutoff = timezone.now() - relativedelta(months=SEARCH_LOG_RETENTION_MONTHS)
        deleted, _ = SearchLog.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} search log(s) older than 12 months.")
