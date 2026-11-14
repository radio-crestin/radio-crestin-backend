#!/bin/bash

set -e

# No --beat: the schedule runs in exactly one place, scripts/run-beat.sh (one
# beat per worker pod queued every periodic task once per pod).

# Check the DEBUG environment variable
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ] || [ "$DEBUG" = "t" ]; then
    # Run watchmedo auto-restart
    watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A superapp worker --loglevel=INFO --concurrency=5 -Q priority
else
    # Run the celery worker
    celery -A superapp worker --loglevel=INFO --concurrency=5 -Q priority
fi
