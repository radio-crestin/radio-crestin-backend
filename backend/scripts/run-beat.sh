#!/bin/bash

set -e

# The one Celery beat: it queues every periodic task (CELERY_BEAT_SCHEDULE and
# the admin's Periodic Tasks). Run exactly ONE of these per environment; the
# workers no longer start their own.
BEAT="celery -A superapp beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler --pidfile="

if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ] || [ "$DEBUG" = "t" ]; then
    exec watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- $BEAT
else
    exec $BEAT
fi
