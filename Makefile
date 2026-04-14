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

create_backup:
	docker-compose run web python3 manage.py create_backup --file backups/backup.zip --backup-type essential_data

restore_backup:
	docker-compose run web python3 manage.py restore_backup --file backups/backup.zip --backup-type essential_data

# Release
create-new-release-locally:
	bash deploy/scripts/create-new-release.sh local

create-new-release:
	bash deploy/scripts/create-new-release.sh remote

# Live Streaming Dev
STREAM_STATION ?= radio-eldad
STREAM_URL ?= https://c40.radioboss.fm/stream/170

dev-stream-build:
	docker build --load -t live-streaming-dev backend_streams_transcoding/live_streaming/

dev-stream: dev-stream-build
	@docker stop live-stream-dev 2>/dev/null || true
	docker run --rm -d --name live-stream-dev \
		-e STATION_SLUG=$(STREAM_STATION) \
		-e STREAM_URL=$(STREAM_URL) \
		-e S3_ENDPOINT="" \
		-e S3_BUCKET="" \
		-p 8080:8080 \
		live-streaming-dev
	@echo ""
	@echo "=== Live stream dev running ==="
	@echo "  DASH manifest: http://localhost:8080/dash/manifest.mpd"
	@echo "  HLS playlist:  http://localhost:8080/index.m3u8"
	@echo "  Health:         http://localhost:8080/health"
	@echo ""
	@echo "  Dev player:     opening in browser..."
	@echo "  Logs:           make dev-stream-logs"
	@echo "  Stop:           make dev-stream-stop"
	@echo ""
	@sleep 2 && open http://localhost:8080/

dev-stream-logs:
	docker logs -f live-stream-dev

dev-stream-stop:
	docker stop live-stream-dev

dev-stream-test: dev-stream-build
	@docker stop live-stream-dev 2>/dev/null || true
	docker run --rm -d --name live-stream-dev \
		-e STATION_SLUG=$(STREAM_STATION) \
		-e STREAM_URL=$(STREAM_URL) \
		-e S3_ENDPOINT="" \
		-e S3_BUCKET="" \
		-p 8080:8080 \
		live-streaming-dev
	@echo "Waiting for segments to build up..."
	@sleep 15
	python3 -m pytest backend_streams_transcoding/tests/test_hls_stream.py -v
	@docker stop live-stream-dev
