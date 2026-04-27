import sys
from os import environ

import posthog
from django.apps import AppConfig
from django.core.signals import got_request_exception


def _capture_request_exception(sender=None, request=None, **_):
    """Catch any exception that escaped the request handler.

    PosthogContextMiddleware captures exceptions, but only after the
    middleware chain executes — exceptions before/after that window
    (e.g. handler resolution, response middleware crashes) bypass it.
    Django's got_request_exception signal fires for all of them.
    """
    if not environ.get("POSTHOG_API_KEY"):
        return
    try:
        exc = sys.exc_info()[1]
        if exc is None:
            return
        if hasattr(posthog, "capture_exception"):
            posthog.capture_exception(exc, distinct_id="django-request")
        else:
            import traceback
            posthog.capture(
                distinct_id="django-request",
                event="$exception",
                properties={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
    except Exception:
        pass


def _install_excepthook():
    """Last-resort safety net for management commands / standalone scripts /
    threads that crash with an unhandled exception. Django request middleware
    and Celery's task_failure signal cover the common cases; this catches
    everything else.
    """
    if not environ.get("POSTHOG_API_KEY"):
        return
    original = sys.excepthook

    def _hook(exc_type, exc_value, tb):
        try:
            if hasattr(posthog, "capture_exception"):
                posthog.capture_exception(exc_value, distinct_id="django-process")
            posthog.flush()
        except Exception:
            pass
        original(exc_type, exc_value, tb)

    sys.excepthook = _hook


class PosthogErrorTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superapp.apps.posthog_error_tracking'

    def ready(self):
        posthog_api_key = environ.get('POSTHOG_API_KEY', '')
        posthog_host = environ.get('POSTHOG_HOST', 'https://eu.i.posthog.com')

        if not posthog_api_key:
            return

        posthog.api_key = posthog_api_key
        posthog.host = posthog_host

        # Existing handlers: 4xx/5xx + custom view-level capture
        from . import error_handlers
        error_handlers.register_global_error_handlers()

        # Catch exceptions that escape the request handler
        got_request_exception.connect(_capture_request_exception, weak=False)

        # Catch task crashes that never reach Django's request cycle
        try:
            from . import celery_signals
            celery_signals.register_celery_signal_handlers()
        except ImportError:
            # Celery not installed in this process — fine
            pass

        # Catch anything else (management commands, standalone scripts)
        _install_excepthook()
