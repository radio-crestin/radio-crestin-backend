import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from web.models import StationsNowPlaying, StationsUptime


class Command(BaseCommand):
    help = 'Delete old data'

    def handle(self, *args, **options):
        while True:
            try:
                print("Starting to delete old data..")
                StationsUptime.objects.raw("DELETE FROM stations_uptime WHERE timestamp < NOW() - interval '30 days'")
                StationsNowPlaying.objects.raw("DELETE FROM stations_now_playing WHERE timestamp < NOW() - interval '30 days'")
                print("The old data has been deleted successfully")
            except Exception as e:
                print("Error while deleting old data", e)

            # Sleep for one hour
            print("Waiting one hour..")
            time.sleep(60 * 60)
