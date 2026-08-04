import logging
import os
import threading
import time

import django
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

logger = logging.getLogger(__name__)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'superapp.settings')

# Liveness heartbeat. The Kubernetes probe used to run
# `celery -A superapp inspect ping`, which boots a whole Django process (~500MB,
# several seconds of imports) on every check and then waits for a broadcast
# reply over Redis. On a busy node that regularly blew past the probe timeout,
# so the kubelet killed workers that were perfectly healthy — and each restart
# added another import storm, making the next probe more likely to fail.
#
# Instead the worker touches a file from a background thread and the probe just
# stats it. Checking liveness now costs no Python startup at all. If the worker
# process dies or wedges hard enough to stop scheduling threads, the file goes
# stale and the probe fails for a real reason.
HEARTBEAT_FILE = os.environ.get('CELERY_HEARTBEAT_FILE', '/tmp/celery-heartbeat')
HEARTBEAT_INTERVAL_SECONDS = int(os.environ.get('CELERY_HEARTBEAT_INTERVAL', '15'))

_heartbeat_stop = threading.Event()

celery_app = Celery('superapp')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
celery_app.autodiscover_tasks()


celery_app.conf.timezone = 'UTC'


def _touch_heartbeat():
    """Refresh the heartbeat file's mtime, which is all the probe reads."""
    with open(HEARTBEAT_FILE, 'a'):
        os.utime(HEARTBEAT_FILE, None)


def _heartbeat_loop():
    while not _heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
        try:
            _touch_heartbeat()
        except OSError as e:
            # Never let a transient filesystem error kill the thread; a missed
            # beat is recoverable, a dead thread would fail the probe forever.
            logger.warning("Could not write celery heartbeat file: %s", e)


@worker_ready.connect
def start_heartbeat(**kwargs):
    """Begin the liveness heartbeat once the worker is actually serving."""
    try:
        _touch_heartbeat()
    except OSError as e:
        logger.warning("Could not write initial celery heartbeat file: %s", e)

    thread = threading.Thread(
        target=_heartbeat_loop, name='celery-heartbeat', daemon=True
    )
    thread.start()


@worker_shutdown.connect
def stop_heartbeat(**kwargs):
    """Stop beating and remove the file so a stopped worker never looks alive."""
    _heartbeat_stop.set()
    try:
        os.remove(HEARTBEAT_FILE)
    except OSError:
        pass


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
