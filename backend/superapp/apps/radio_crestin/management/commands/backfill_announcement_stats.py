"""Rebuilds every announcement's hourly and daily history from the kept events (run once at deploy; safe to rerun)."""
import time

from django.core.management.base import BaseCommand

from ...services import announcement_stat_buckets


class Command(BaseCommand):
    help = "Rebuilds the announcements' hourly and daily history from the raw events."

    def handle(self, *args, **options):
        started = time.monotonic()
        written = announcement_stat_buckets.rebuild()
        self.stdout.write(f'{written} buckets written in {time.monotonic() - started:.1f} s')
