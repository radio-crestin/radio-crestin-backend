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
create-new-release:
	@set -e; \
	ROOT_DIR="$$(pwd)"; \
	CONFIG_ENV_YAML="$$ROOT_DIR/deploy/environments/radio_crestin_production/secrets/config_env.yaml"; \
	export CONFIG_YAML_PATH="$$CONFIG_ENV_YAML"; \
	CURRENT_TAG=$$(grep 'IMAGES_TAG:' "$$CONFIG_ENV_YAML" | awk '{print $$2}'); \
	MAJOR=$$(echo "$$CURRENT_TAG" | sed 's/v//' | cut -d. -f1); \
	MINOR=$$(echo "$$CURRENT_TAG" | sed 's/v//' | cut -d. -f2); \
	PATCH=$$(echo "$$CURRENT_TAG" | sed 's/v//' | cut -d. -f3); \
	NEXT_PATCH=$$((PATCH + 1)); \
	NEXT_TAG="v$$MAJOR.$$MINOR.$$NEXT_PATCH"; \
	echo "=== Creating new release: $$CURRENT_TAG -> $$NEXT_TAG ==="; \
	echo "Step 1: Bumping IMAGES_TAG to $$NEXT_TAG..."; \
	sed -i '' "s/IMAGES_TAG: $$CURRENT_TAG/IMAGES_TAG: $$NEXT_TAG/" "$$CONFIG_ENV_YAML"; \
	echo "Step 2: Building all Docker images..."; \
	cd "$$ROOT_DIR/deploy/environments/radio_crestin_production" && bash ../../scripts/build-all-docker-images.sh; \
	echo "Step 3: Generating manifests..."; \
	cd "$$ROOT_DIR/deploy/environments/radio_crestin_production" && bash ../../scripts/generate-manifests.sh; \
	echo "Step 4: Committing and pushing deploy..."; \
	cd "$$ROOT_DIR/deploy" && git add -A && git commit -m "chore: release $$NEXT_TAG" && git push; \
	echo "Step 5: Updating deploy submodule reference..."; \
	cd "$$ROOT_DIR" && git add deploy && git commit -m "chore: update deploy submodule to $$NEXT_TAG"; \
	echo "=== Release $$NEXT_TAG created successfully ==="

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
