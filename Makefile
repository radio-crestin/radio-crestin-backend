ifneq ("$(wildcard .env)","")
include .env
export $(shell sed 's/=.*//' .env)

# Update PATH variable
PATH := $(shell sed -n 's/^PATH=//p' .env):$(PATH):/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin
endif

deploy: git-pull
	docker-compose --env-file .env  up --build -d

force-deploy: git-pull
	docker-compose --env-file .env  up -d --build --force-recreate

force-deploy-no-cache: git-pull
	docker-compose --env-file .env  build
	docker-compose --env-file .env  up -d --force-recreate


deploy-staging: git-pull
	docker-compose -f docker-compose.staging.yaml --env-file .env  up --build -d

force-deploy-staging: git-pull
	docker-compose -f docker-compose.staging.yaml --env-file .env  build
	docker-compose -f docker-compose.staging.yaml --env-file .env  up -d --force-recreate

start-docker:
	docker-compose --env-file .env  up --build --force-recreate -d

stop-docker:
	docker-compose stop

stop:
	docker-compose --env-file .env  stop

git-pull:
	git pull origin master;

logs:
	docker-compose logs -f

web-logs:
	docker-compose logs -f -n 100 web

worker-logs:
	docker-compose logs -f -n 100 worker

hls-streaming-logs:
	docker-compose logs -f -n 100 backend-hls-streaming

hls-streaming-bash:
	docker-compose exec -ti backend-hls-streaming bash

create-superuser:
	docker-compose exec admin python manage.py createsuperuser

load-admin-fixtures:
	cd backend && make load-admin-fixtures

# Backend

makemigrations:
	docker-compose run web python3 manage.py makemigrations

migrate:
	docker-compose run web python3 manage.py migrate

createsuperuser:
	docker-compose run web python3 manage.py createsuperuser
