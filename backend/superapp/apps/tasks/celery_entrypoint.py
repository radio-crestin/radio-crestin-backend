import os
import django
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superapp.settings')

celery_app = Celery('superapp')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
celery_app.autodiscover_tasks()

# Configure periodic tasks
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'scrape-all-stations-metadata': {
        'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.scrape_all_stations_metadata',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'scrape-all-stations-rss-feeds': {
        'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.scrape_all_stations_rss_feeds',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'cleanup-old-data': {
        'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'kwargs': {'days_to_keep': 30},
    },
    'weekly-essential-backup': {
        'task': 'backups.automated_weekly_backup',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),  # Weekly on Monday at 3 AM
    },
}

celery_app.conf.timezone = 'UTC'


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
