STREAM_STATION ?= radio-eldad
STREAM_URL ?= https://c40.radioboss.fm/stream/170

dev-build:
	docker build --load -t live-streaming-dev live_streaming/

dev: dev-build
	@docker stop live-stream-dev 2>/dev/null || true
	docker run --rm -d --name live-stream-dev \
		-e STATION_SLUG=$(STREAM_STATION) \
		-e STREAM_URL=$(STREAM_URL) \
		-e S3_ENDPOINT="" \
		-e S3_BUCKET="" \
		-e STREAMING_POD_API_KEY=dev-streaming-key \
		-e DJANGO_GRAPHQL_URL=http://host.docker.internal:8080/v1/graphql \
		-p 8085:8080 \
		live-streaming-dev
	@echo ""
	@echo "=== Live stream dev running ==="
	@echo "  Player:    http://localhost:8085/"
	@echo "  AAC+ HLS:  http://localhost:8085/aac/index.m3u8"
	@echo "  Master:    http://localhost:8085/master.m3u8"
	@echo "  Status:    http://localhost:8085/status.json"
	@echo "  Health:    http://localhost:8085/health"
	@echo ""
	@echo "  Logs:      make dev-logs"
	@echo "  Stop:      make dev-stop"
	@echo "  Test:      make dev-test"
	@echo ""
	@sleep 2 && open http://localhost:8085/

dev-logs:
	docker logs -f live-stream-dev

dev-stop:
	docker stop live-stream-dev

dev-test: dev-build
	@docker stop live-stream-dev 2>/dev/null || true
	docker run --rm -d --name live-stream-dev \
		-e STATION_SLUG=$(STREAM_STATION) \
		-e STREAM_URL=$(STREAM_URL) \
		-e S3_ENDPOINT="" \
		-e S3_BUCKET="" \
		-e STREAMING_POD_API_KEY=dev-streaming-key \
		-e DJANGO_GRAPHQL_URL=http://host.docker.internal:8080/v1/graphql \
		-p 8085:8080 \
		live-streaming-dev
	@echo "Waiting for segments..."
	@sleep 15
	python3 -m pytest tests/test_hls_stream.py -v
	@docker stop live-stream-dev

dev-bash:
	docker exec -it live-stream-dev sh
