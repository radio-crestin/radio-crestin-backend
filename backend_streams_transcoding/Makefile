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
		-p 8080:8080 \
		live-streaming-dev
	@echo ""
	@echo "=== Live stream dev running ==="
	@echo "  Player:    http://localhost:8080/"
	@echo "  AAC+ HLS:  http://localhost:8080/aac/index.m3u8"
	@echo "  Opus HLS:  http://localhost:8080/opus/index.m3u8"
	@echo "  Master:    http://localhost:8080/master.m3u8"
	@echo "  Status:    http://localhost:8080/status.json"
	@echo "  Health:    http://localhost:8080/health"
	@echo ""
	@echo "  Logs:      make dev-logs"
	@echo "  Stop:      make dev-stop"
	@echo "  Test:      make dev-test"
	@echo ""
	@sleep 2 && open http://localhost:8080/

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
		-p 8080:8080 \
		live-streaming-dev
	@echo "Waiting for segments..."
	@sleep 15
	python3 -m pytest tests/test_hls_stream.py -v
	@docker stop live-stream-dev

dev-bash:
	docker exec -it live-stream-dev sh
