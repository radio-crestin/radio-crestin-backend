SHELL := /bin/bash
ifneq ("$(wildcard .env.local)","")
include .env.local
export $(shell sed 's/=.*//' .env.local)

# Update PATH variable
PATH := $(shell sed -n 's/^PATH=//p' .env.local):$(PATH):/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin
endif

venv: venv/touchfile

venv/touchfile: requirements.txt
	test -d venv || virtualenv venv
	touch venv/touchfile

install-requirements: venv/touchfile
	. venv/bin/activate && ./scripts/generate-requirements.sh | pip install --upgrade -r /dev/stdin
	. venv/bin/activate && pip install psycopg2-binary --force-reinstall --no-cache-dir; \
	cd superapp/apps/admin_portal/tailwind && npm install

setup-sample-env:
	cp .env.local.example .env.local;
	cp .env.example .env;

web-bash:
	docker-compose exec -ti web bash

web-logs:
	docker-compose logs -f web -n 1000

start-docker:
	docker-compose up -d --build

force-start-docker:
	docker-compose up -d --build --force-recreate

stop-docker:
	docker-compose stop

destroy-docker:
	docker-compose stop
	docker-compose down -v

makemigrations:
	docker-compose run web python3 manage.py makemigrations

migrate:
	docker-compose run web python3 manage.py migrate

createsuperuser:
	docker-compose run web python3 manage.py createsuperuser

collectstatic:
	docker-compose exec web python3 manage.py collectstatic --no-input

start-tailwind-watch:
	cd superapp/apps/admin_portal/tailwind; \
	npm run tailwind:watch

list_all_permissions:
	docker-compose exec web python3 manage.py list_all_permissions

list_all_urls_patterns:
	docker-compose exec web python3 manage.py list_all_urls_patterns

makemessages:
	mkdir -p site-packages
	ln -s venv/lib/python3.13/site-packages/unfold site-packages/unfold
	ln -s venv/lib/python3.13/site-packages/django site-packages/django
	docker-compose exec web python3 manage.py makemessages -l ro -l en -i venv -s
	rm -rf site-packages

compilemessages:
	docker-compose exec web python3 manage.py compilemessages
	rm -rf site-packages

generate_django_translations:
	docker-compose exec web python3 manage.py generate_django_translations

generate_material_variant_prices:
	docker-compose exec web python3 manage.py generate_material_variant_prices

generate_translation_values:
	docker-compose exec web python3 manage.py generate_translation_values


create-fixtures:
	docker-compose exec web python3 manage.py dumpdata --natural-foreign --natural-primary --indent 2 --output fixtures/fixtures.json

create-fixtures-all:
	mkdir -p fixtures/tables
	docker-compose exec web python3 manage.py dumpdata radio_crestin.posts --natural-foreign --natural-primary --indent 2 --output fixtures/tables/posts.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationsnowplaying --natural-foreign --natural-primary --indent 2 --output fixtures/tables/stations_now_playing.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationsuptime --natural-foreign --natural-primary --indent 2 --output fixtures/tables/stations_uptime.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stations --natural-foreign --natural-primary --indent 2 --output fixtures/tables/stations.json
	docker-compose exec web python3 manage.py dumpdata auth.user --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_user.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationgroups --natural-foreign --natural-primary --indent 2 --output fixtures/tables/station_groups.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationstreams --natural-foreign --natural-primary --indent 2 --output fixtures/tables/station_streams.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.reviews --natural-foreign --natural-primary --indent 2 --output fixtures/tables/reviews.json
	docker-compose exec web python3 manage.py dumpdata auth.permission --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_permission.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationtostationgroup --natural-foreign --natural-primary --indent 2 --output fixtures/tables/station_to_station_group.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationmetadatafetchcategories --natural-foreign --natural-primary --indent 2 --output fixtures/tables/station_metadata_fetch_categories.json
	docker-compose exec web python3 manage.py dumpdata radio_crestin.stationsmetadatafetch --natural-foreign --natural-primary --indent 2 --output fixtures/tables/stations_metadata_fetch.json
	docker-compose exec web python3 manage.py dumpdata auth.group_permissions --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_group_permissions.json
	docker-compose exec web python3 manage.py dumpdata auth.user_groups --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_user_groups.json
	docker-compose exec web python3 manage.py dumpdata auth.user_user_permissions --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_user_user_permissions.json
	docker-compose exec web python3 manage.py dumpdata auth.group --natural-foreign --natural-primary --indent 2 --output fixtures/tables/auth_group.json
	docker-compose exec web python3 manage.py dumpdata --natural-foreign --natural-primary --indent 2 --output fixtures/all_tables.json

load-fixtures:
	docker-compose exec web python3 manage.py loaddata \
		fixtures/fixtures
