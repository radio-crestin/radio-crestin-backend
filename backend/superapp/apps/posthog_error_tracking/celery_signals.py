"""
Celery signal handlers — capture every task failure to PostHog.

Without this, exceptions raised inside Celery tasks never reach Django's
request middleware (where PosthogContextMiddleware would have caught them).
The task_failure signal fires after retries are exhausted, so this captures
genuine failures, not transient errors that recovered on retry.
"""

from os import environ

import posthog
from celery.signals import task_failure


def _capture_task_failure(sender=None, task_id=None, exception=None,
                          args=None, kwargs=None, einfo=None, **_):
    if not environ.get("POSTHOG_API_KEY"):
        return
    try:
        properties = {
            "task_name": getattr(sender, "name", "unknown"),
            "task_id": task_id,
            "task_args": repr(args)[:1000] if args else "",
            "task_kwargs": repr(kwargs)[:1000] if kwargs else "",
            "error_type": type(exception).__name__ if exception else "Unknown",
            "error_message": str(exception) if exception else "",
            "traceback": str(einfo) if einfo else "",
            "service": "celery-worker",
            "$process_person_profile": False,
        }
        if exception is not None and hasattr(posthog, "capture_exception"):
            posthog.capture_exception(
                exception,
                distinct_id="celery-worker",
                properties=properties,
            )
        else:
            posthog.capture(
                distinct_id="celery-worker",
                event="celery_task_failed",
                properties=properties,
            )
    except Exception:
        # Never let reporting break the worker.
        pass


def register_celery_signal_handlers():
    """Wire up Celery signals at Django app ready()."""
    task_failure.connect(_capture_task_failure, weak=False)
