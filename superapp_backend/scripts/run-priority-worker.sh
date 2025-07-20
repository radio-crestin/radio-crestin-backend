#!/bin/bash

set -e

# Check the DEBUG environment variable
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ] || [ "$DEBUG" = "t" ]; then
    # Run watchmedo auto-restart
    watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A superapp worker --loglevel=INFO --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --concurrency=5 -Q priority
else
    # Run the celery worker
    celery -A superapp worker --loglevel=INFO --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --concurrency=5 -Q priority
fi
