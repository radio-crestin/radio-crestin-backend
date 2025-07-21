from django.apps import AppConfig
import posthog
from os import environ


class PosthogErrorTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'posthog_error_tracking'
    
    def ready(self):
        posthog.api_key = environ.get('POSTHOG_API_KEY', '')
        posthog.host = environ.get('POSTHOG_HOST', 'https://eu.i.posthog.com')
