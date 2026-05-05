STREAM_STATION ?= radio-gosen
STREAM_URL ?= https://sp.totalstreaming.net/8125/stream

dev-build:
	docker build --load -t live-streaming-dev live_streaming/

dev: dev-build
	@docker stop live-stream-dev 2>/dev/null || true
	docker run --rm -d --name live-stream-dev \
		-e STATION_SLUG=$(STREAM_STATION) \
		-e STREAM_URL=$(STREAM_URL) \
		-e STREAMING_POD_API_KEY=dev-streaming-key \
		-e DJANGO_API_URL=host.docker.internal:8080 \
		-e DJANGO_GRAPHQL_URL=http://host.docker.internal:8080/v1/graphql \
		-p 8085:8080 \
		live-streaming-dev
	@echo ""
	@echo "=== Live stream dev running ==="
	@echo "  Player:    http://localhost:8085/"
	@echo "  AAC+ HLS:  http://localhost:8085/aac/index.m3u8"
	@echo "  Master:    http://localhost:8085/master.m3u8"
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

# Long-duration spec validation — runs Apple's mediastreamvalidator for
# DEV_TEST_LONG_SECS (default 900s = 15 min). Required catch for multi-fetch
# DATERANGE bugs (e.g. "Removed an EXT-X-DATERANGE while mapped to range in
# playlist") that short runs miss. Pick a music-heavy station so a song
# change actually happens during the run.
DEV_TEST_LONG_SECS ?= 900
dev-test-long:
	@which mediastreamvalidator >/dev/null || { echo "mediastreamvalidator not found — install Apple HLS Tools"; exit 1; }
	@echo "Running mediastreamvalidator on http://localhost:8085/master.m3u8 for $(DEV_TEST_LONG_SECS)s..."
	@echo "Pass criterion: zero CRITICAL and zero MUST-fix issues."
	@timeout $(DEV_TEST_LONG_SECS) mediastreamvalidator http://localhost:8085/master.m3u8 2>&1 | tee /tmp/dev-test-long.log
	@echo
	@if grep -qE "CRITICAL|MUST fix" /tmp/dev-test-long.log; then \
		echo "❌ FAIL — validator surfaced spec violations (see /tmp/dev-test-long.log)"; \
		grep -A3 "CRITICAL\|MUST fix" /tmp/dev-test-long.log; \
		exit 1; \
	else \
		echo "✓ PASS — no critical or MUST-fix issues across $(DEV_TEST_LONG_SECS)s"; \
	fi
