from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from celery.schedules import crontab
from os import environ


def extend_superapp_settings(main_settings):
    """Extend main SuperApp settings with radio_crestin_scraping app configuration."""

    # Add this app to INSTALLED_APPS
    main_settings['INSTALLED_APPS'] += ['superapp.apps.radio_crestin_scraping']

    # Configure Celery settings for radio station scraping
    celery_settings = {
        'CELERY_BROKER_URL': main_settings.get('REDIS_BROKER_URL', 'redis://localhost:6379/0'),
        'CELERY_RESULT_BACKEND': main_settings.get('REDIS_BROKER_URL', 'redis://localhost:6379/0'),
        'CELERY_ACCEPT_CONTENT': ['json'],
        'CELERY_TASK_SERIALIZER': 'json',
        'CELERY_RESULT_SERIALIZER': 'json',
        'CELERY_TIMEZONE': 'UTC',
        'CELERY_ENABLE_UTC': True,
        'CELERY_TASK_TRACK_STARTED': True,
        'CELERY_TASK_TIME_LIMIT': 30 * 60,  # 30 minutes
        'CELERY_TASK_SOFT_TIME_LIMIT': 25 * 60,  # 25 minutes
        'CELERY_WORKER_PREFETCH_MULTIPLIER': 1,
        'CELERY_TASK_ACKS_LATE': True,
        'CELERY_WORKER_MAX_TASKS_PER_CHILD': 50,
    }

    # Update main settings with Celery configuration
    main_settings.update(celery_settings)

    # Configure Celery beat schedule for radio station scraping tasks
    # Only create scheduled tasks in production (when DEBUG is False)
    is_debug = environ.get("DEBUG", 'false') == 'true'
    
    if not is_debug:
        beat_schedule = {
            'scrape-all-stations-metadata': {
                'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.scrape_all_stations_metadata',
                'schedule': 30.0,  # Every 30 seconds
            },
            'scrape-all-stations-rss-feeds': {
                'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.scrape_all_stations_rss_feeds',
                'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            },
            'cleanup-old-data': {
                'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.cleanup_old_scraped_data',
                'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
                'kwargs': {'days_to_keep': 30},
            },
            'check-stations-uptime': {
                'task': 'superapp.apps.radio_crestin_scraping.tasks.scraping_tasks.check_all_stations_uptime',
                'schedule': 300.0,  # Every 5 minutes (300 seconds)
            },
        }

        # Add beat schedule to Celery configuration
        main_settings['CELERY_BEAT_SCHEDULE'] = main_settings.get('CELERY_BEAT_SCHEDULE', {})
        main_settings['CELERY_BEAT_SCHEDULE'].update(beat_schedule)
