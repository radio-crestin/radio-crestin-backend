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

load-fixtures:
	docker-compose exec web python3 manage.py loaddata \
		fixtures/fixtures

sync-prod-db-clean:
	@echo "Creating backup of local database..."
	@docker-compose exec -T postgres pg_dump -U postgres -d postgres > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Truncating local tables..."
	@psql postgres://postgres:postgrespassword@127.0.0.1:5432/postgres -c "\
		TRUNCATE TABLE \
		auth_user_user_permissions, \
		auth_user_groups, \
		auth_group_permissions, \
		stations_metadata_fetch, \
		station_to_station_group, \
		station_streams, \
		reviews, \
		posts, \
		stations_uptime, \
		stations_now_playing, \
		stations, \
		auth_user, \
		auth_permission, \
		auth_group, \
		station_groups, \
		station_metadata_fetch_categories, \
		django_migrations, \
		django_content_type \
		CASCADE;"
	@echo "Exporting data from production database..."
	@ssh root@168.119.107.195 "docker exec ab370527d2bb pg_dump -U postgres -d postgres \
		--data-only --disable-triggers \
		-t posts -t stations_now_playing -t stations_uptime -t stations -t auth_user \
		-t station_groups -t station_streams -t reviews -t auth_permission \
		-t station_to_station_group -t station_metadata_fetch_categories \
		-t django_content_type -t stations_metadata_fetch -t django_migrations \
		-t auth_group_permissions -t auth_user_groups -t auth_user_user_permissions \
		-t auth_group" | psql postgres://postgres:postgrespassword@127.0.0.1:5432/postgres
	@echo "Database sync completed!"

