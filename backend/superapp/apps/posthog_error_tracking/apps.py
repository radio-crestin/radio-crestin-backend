from django.apps import AppConfig
import posthog
from os import environ


class PosthogErrorTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superapp.apps.posthog_error_tracking'
    
    def ready(self):
        # Initialize PostHog with environment variables
        posthog_api_key = environ.get('POSTHOG_API_KEY', '')
        posthog_host = environ.get('POSTHOG_HOST', 'https://eu.i.posthog.com')
        
        if posthog_api_key:
            posthog.api_key = posthog_api_key
            posthog.host = posthog_host
            
            # Import and register global error handlers
            from . import error_handlers
            error_handlers.register_global_error_handlers()
