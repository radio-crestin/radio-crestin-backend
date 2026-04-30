#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
# 60 segments × 6s = 6 minutes sliding window
HLS_LIST_SIZE="${HLS_LIST_SIZE:-60}"
# Keep segments on disk past the playlist window so that lagging clients,
# CDN cache misses, and stale player playlists don't 404.
# On-disk lifetime = (HLS_LIST_SIZE + HLS_DELETE_THRESHOLD) × SEGMENT_DURATION.
# Default 100 → (60 + 100) × 6 = 960s ≈ 16 min, giving ≥15 min retention.
HLS_DELETE_THRESHOLD="${HLS_DELETE_THRESHOLD:-100}"

export SEGMENT_DURATION

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "HLS:     AAC-LC 96k, ${SEGMENT_DURATION}s segments, ${HLS_LIST_SIZE} in playlist, ${HLS_DELETE_THRESHOLD} retained past window"

# Fire a pod-startup event so PostHog timelines line up with restarts.
python3 /app/scripts/report_event.py pod_started \
    --prop segment_duration="$SEGMENT_DURATION" \
    --prop hls_list_size="$HLS_LIST_SIZE" \
    --prop hls_delete_threshold="$HLS_DELETE_THRESHOLD" >/dev/null 2>&1 &

# Directory layout:
#   /data/hls/aac/live.m3u8              FFmpeg-managed live playlist
#   /data/hls/aac/1713200400.ts           FFmpeg-managed segments (epoch timestamp)
mkdir -p /data/hls/aac /data/metadata

# Render NGINX config with env vars
envsubst '${STATION_SLUG}' < /app/nginx/nginx.conf > /tmp/nginx/nginx.conf

echo "Starting NGINX..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

echo "Starting health server..."
python3 /app/scripts/health_server.py &
HEALTH_PID=$!

echo "Starting metadata monitor..."
python3 /app/scripts/metadata_monitor.py &
METADATA_PID=$!

echo "Starting ID3 injector..."
python3 /app/scripts/id3_injector.py &
ID3_PID=$!

echo "Starting scraper engine..."
python3 /app/scripts/scraper_engine.py &
SCRAPER_PID=$!

echo "Starting mel analyzer..."
python3 /app/scripts/mel_analyzer.py &
MEL_PID=$!

echo "Starting playlist generator..."
python3 /app/scripts/playlist_generator.py &
PLAYLIST_PID=$!

echo "Starting log monitor..."
python3 /app/scripts/log_monitor.py &
LOG_MONITOR_PID=$!

echo "Starting stream monitor..."
python3 /app/scripts/stream_monitor.py &
STREAM_MONITOR_PID=$!

echo "Starting segment cleanup (30min max)..."
sh /app/scripts/cleanup.sh &
CLEANUP_PID=$!

cleanup() {
    echo "Shutting down gracefully..."
    kill -TERM "$FFMPEG_LOOP_PID" 2>/dev/null || true
    kill -TERM "$FFMPEG_PID" 2>/dev/null || true
    kill -TERM "$METADATA_PID" "$ID3_PID" "$SCRAPER_PID" "$MEL_PID" "$PLAYLIST_PID" "$LOG_MONITOR_PID" "$STREAM_MONITOR_PID" "$CLEANUP_PID" 2>/dev/null || true
    kill -TERM "$HEALTH_PID" 2>/dev/null || true
    sleep 5
    kill -TERM "$NGINX_PID" 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── FFmpeg: standard HLS output ──
# Uses -f hls so ffmpeg manages both the playlist and segments.
# This is the standard, battle-tested approach for live HLS.
#
# Key flags:
#   -hls_time         — target segment duration
#   -hls_list_size    — number of segments in the playlist (sliding window)
#   -hls_flags delete_segments — auto-delete old segments outside the window
#   -hls_segment_type mpegts   — MPEG-TS container
#   -hls_segment_filename      — segment naming pattern
#
FFMPEG_RETRY_DELAY=10
FFMPEG_MAX_RETRY_DELAY=120
FFMPEG_PID=""

start_ffmpeg() {
    echo "Starting FFmpeg (HLS, ${SEGMENT_DURATION}s, ${HLS_LIST_SIZE} segments)..."
    # This mirrors the flag set from the old backend_hls_streaming pipeline (commit 79d019d),
    # minus three items that conflict with the current architecture:
    #   - hls_flag program_date_time:  Python playlist_generator.py injects PDT from the
    #                                  epoch segment filename; duplicating PDT breaks players.
    #   - hls_start_number_source epoch: incompatible with -strftime 1 (epoch-named segments).
    #   - master_pl_publish_rate: no ffmpeg-emitted master; static master served by Python.
    # Input resilience: reconnect with exponential backoff (1s,2s,4s); ffmpeg gives up once
    # the next backoff would exceed reconnect_delay_max=4 (~3 retries), then bash loop restarts.
    ffmpeg -loglevel warning \
        -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 \
        -reconnect_delay_max 4 \
        -fflags +genpts+discardcorrupt -max_delay 5000000 \
        -i "$STREAM_URL" -y \
        -map 0:a:0 -c:a libfdk_aac -profile:a aac_low -b:a 96k \
        -flags +global_header -async 1 -ac 2 -ar 44100 \
        -bufsize 30000000 -sc_threshold 0 \
        -f hls \
            -hls_init_time "$SEGMENT_DURATION" \
            -hls_time "$SEGMENT_DURATION" \
            -hls_list_size "$HLS_LIST_SIZE" \
            -hls_delete_threshold "$HLS_DELETE_THRESHOLD" \
            -hls_flags delete_segments+independent_segments+split_by_time+omit_endlist \
            -hls_segment_type mpegts \
            -hls_segment_options 'mpegts_flags=+initial_discontinuity' \
            -strftime 1 \
            -hls_segment_filename '/data/hls/aac/%s.ts' \
            '/data/hls/aac/live.m3u8' &
    FFMPEG_PID=$!
    echo "FFmpeg started (PID $FFMPEG_PID)"
}

ffmpeg_loop() {
    local delay=$FFMPEG_RETRY_DELAY
    local restarts=0
    local started_at
    local ran_for
    while true; do
        started_at=$(date +%s)
        start_ffmpeg
        wait "$FFMPEG_PID" || true
        local exit_code=$?
        ran_for=$(( $(date +%s) - started_at ))
        restarts=$((restarts + 1))
        echo "ffmpeg_loop: ffmpeg exited (code=${exit_code}, ran=${ran_for}s, restart_count=${restarts}); retrying in ${delay}s"
        # Fire-and-forget event to PostHog. Errors here must never break the supervisor.
        python3 /app/scripts/report_event.py ffmpeg_exit \
            --prop exit_code="$exit_code" \
            --prop ran_for="$ran_for" \
            --prop restart_count="$restarts" \
            --prop retry_delay="$delay" >/dev/null 2>&1 &
        sleep "$delay"
        delay=$((delay * 2))
        if [ "$delay" -gt "$FFMPEG_MAX_RETRY_DELAY" ]; then
            delay=$FFMPEG_MAX_RETRY_DELAY
        fi
    done
}

ffmpeg_loop &
FFMPEG_LOOP_PID=$!

# Wait for any critical background process to exit
wait -n "$NGINX_PID" || true
echo "Critical process exited, shutting down..."
cleanup
