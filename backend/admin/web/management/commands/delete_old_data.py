import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from web.models import StationsNowPlaying, StationsUptime


class Command(BaseCommand):
    help = 'Delete old data'

    def handle(self, *args, **options):
        while True:
            print("Starting to delete old data..")
            d = datetime.today() - timedelta(days=30)
            StationsNowPlaying.objects.filter(timestamp__lte=d).delete()
            StationsUptime.objects.filter(timestamp__lte=d).delete()
            print("The old data has been deleted successfully")

            # Sleep for one hour
            print("Waiting one hour..")
            time.sleep(60 * 60)
