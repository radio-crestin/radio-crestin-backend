from django.core.management.base import BaseCommand
from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
    scrape_all_stations_metadata,
    scrape_all_stations_rss_feeds
)


class Command(BaseCommand):
    help = 'Test radio scraping functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--station-id',
            type=int,
            help='Test scraping for a specific station ID',
        )
        parser.add_argument(
            '--rss-only',
            action='store_true',
            help='Only test RSS feed scraping',
        )
        parser.add_argument(
            '--metadata-only',
            action='store_true',
            help='Only test metadata scraping',
        )

    def handle(self, *args, **options):
        station_id = options.get('station_id')
        rss_only = options.get('rss_only')
        metadata_only = options.get('metadata_only')

        if station_id:
            if not rss_only:
                self.stdout.write(f'Testing metadata scraping for station {station_id}...')
                from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_metadata
                result = scrape_station_metadata.delay(station_id)
                self.stdout.write(f'Task queued: {result.id}')
            
            if not metadata_only:
                self.stdout.write(f'Testing RSS scraping for station {station_id}...')
                from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import scrape_station_rss_feed
                result = scrape_station_rss_feed.delay(station_id)
                self.stdout.write(f'Task queued: {result.id}')
        else:
            if not rss_only:
                self.stdout.write('Testing all stations metadata scraping...')
                result = scrape_all_stations_metadata.delay()
                self.stdout.write(f'Task queued: {result.id}')
            
            if not metadata_only:
                self.stdout.write('Testing all stations RSS scraping...')
                result = scrape_all_stations_rss_feeds.delay()
                self.stdout.write(f'Task queued: {result.id}')

        self.stdout.write(
            self.style.SUCCESS('Scraping tasks queued successfully. Check Celery worker logs for results.')
        )