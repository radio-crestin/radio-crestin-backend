#!/bin/bash
set -e;

# Check the DEBUG environment variable
if [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ] || [ "$DEBUG" = "t" ]; then
  python manage.py migrate
  python manage.py collectstatic --noinput
  python manage.py runserver 0.0.0.0:8080
else
  gunicorn --bind :8080 --workers 2 superapp.wsgi
fi
