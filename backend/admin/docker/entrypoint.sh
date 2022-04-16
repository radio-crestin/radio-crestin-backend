#!/bin/bash

set -e

echo "Waiting for Postgresql to be available.."
/src/docker/wait-for-it.sh -h "$(echo $ADMIN_DATABASE_URL | sed -r 's/(.+)@(.+)\:([0-9]+)(.+)/\2/')" -p "$(echo $ADMIN_DATABASE_URL | sed -r 's/(.+)@(.+)\:([0-9]+)(.+)/\3/')"

echo "Wait 5 more seconds"
sleep 5

cd /src

echo "Collecting static assets.."
rm -rf /data/static
mkdir -p /data/static
python3 manage.py collectstatic --clear --noinput &

echo "Running migrations.."
python3 manage.py migrate

echo "Testing the Django server.."
python3 manage.py test --keepdb

# TODO: move these fixtures to Hasura
#echo "Applying fixtures.."
#python manage.py loaddata apps/fixtures.yaml

if [[ "$DEBUG" == "true" ]]; then
  echo "Starting the Django server in debug mode.."
  python3 manage.py runserver 0.0.0.0:8080
else
  echo "Starting the Nginx server.."
  nginx

  echo "Starting the Django server.."
  python3 manage.py runserver 127.0.0.1:5000
fi
