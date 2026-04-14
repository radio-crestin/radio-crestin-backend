#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"

export SEGMENT_DURATION

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "HLS:     AAC+ 64k"

# Directory layout:
#   /data/hls/aac/segments/<epoch>.ts    HE-AAC 64k segments (clock-aligned)
mkdir -p /data/hls/aac/segments

# Record pod start time for gap tracking
date +%s > /data/pod_started_at

# Render NGINX config with env vars
envsubst '${STATION_SLUG}' < /app/nginx/nginx.conf > /tmp/nginx/nginx.conf

echo "Starting NGINX..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

echo "Starting playlist generator..."
python3 /app/scripts/playlist_generator.py &
PLAYLIST_PID=$!

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

echo "Starting cleanup..."
/app/scripts/cleanup.sh &
CLEANUP_PID=$!

cleanup() {
    echo "Shutting down gracefully..."
    # 1. Stop FFmpeg loop and FFmpeg process (stop producing new segments)
    kill -TERM "$FFMPEG_LOOP_PID" 2>/dev/null || true
    kill -TERM "$FFMPEG_PID" 2>/dev/null || true
    # 2. Stop metadata/scraping processes
    kill -TERM "$METADATA_PID" "$ID3_PID" "$CLEANUP_PID" "$SCRAPER_PID" "$MEL_PID" 2>/dev/null || true
    # 3. Kill health server so readiness probe fails
    kill -TERM "$HEALTH_PID" 2>/dev/null || true
    # 4. Keep NGINX alive to serve cached segments for in-flight requests
    sleep 5
    # 5. Stop NGINX and playlist generator
    kill -TERM "$NGINX_PID" "$PLAYLIST_PID" 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── FFmpeg: clock-aligned segments ──
# Uses -f segment (not -f hls) with -segment_atclocktime 1 for deterministic,
# wall-clock-aligned segment boundaries.  Segment filenames = Unix epoch.
# This means any m3u8 can be generated from pure math — no file I/O needed.
#
# Key flags:
#   -segment_atclocktime 1  — snap to wall-clock multiples (e.g. :00, :06, :12)
#   -strftime 1             — name files with epoch (%s.ts)
#   -segment_format mpegts  — MPEG-TS container for HLS compatibility
#   (no -reset_timestamps — continuous PTS across segments avoids audio glitches)
#
# Retry loop: if FFmpeg exits (e.g. upstream timeout), restart it instead of
# killing the entire pod.  NGINX/playlist/health keep running.
FFMPEG_RETRY_DELAY=10
FFMPEG_MAX_RETRY_DELAY=120
FFMPEG_PID=""

start_ffmpeg() {
    echo "Starting FFmpeg (clock-aligned segments, ${SEGMENT_DURATION}s)..."
    ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_delay_max 30 \
        -i "$STREAM_URL" -y \
        -map 0:a:0 -c:a libfdk_aac -profile:a aac_he -b:a 64k -ac 2 -ar 44100 \
        -f segment \
            -segment_time "$SEGMENT_DURATION" \
            -segment_atclocktime 1 \
            -strftime 1 \
            -segment_format mpegts \
            '/data/hls/aac/segments/%s.ts' &
    FFMPEG_PID=$!
    echo "FFmpeg started (PID $FFMPEG_PID)"

    # Remove the initial partial segment (non-aligned).
    # -segment_atclocktime aligns SUBSEQUENT segments to clock multiples,
    # but the first segment starts whenever FFmpeg connects (mid-cycle).
    # Wait for 2 aligned segments, then delete any non-aligned ones.
    (
        sleep $((SEGMENT_DURATION * 3))
        for f in /data/hls/aac/segments/*.ts; do
            num=$(basename "$f" .ts)
            if [ $((num % SEGMENT_DURATION)) -ne 0 ] 2>/dev/null; then
                echo "Removing non-aligned segment: $(basename $f)"
                rm -f "$f"
            fi
        done
    ) &
}

ffmpeg_loop() {
    local delay=$FFMPEG_RETRY_DELAY
    while true; do
        start_ffmpeg
        wait "$FFMPEG_PID" || true
        echo "FFmpeg exited, retrying in ${delay}s..."
        sleep "$delay"
        # Exponential backoff capped at max delay
        delay=$((delay * 2))
        if [ "$delay" -gt "$FFMPEG_MAX_RETRY_DELAY" ]; then
            delay=$FFMPEG_MAX_RETRY_DELAY
        fi
    done
}

ffmpeg_loop &
FFMPEG_LOOP_PID=$!

# Wait for any critical background process to exit
wait -n "$NGINX_PID" "$PLAYLIST_PID" || true
echo "Critical process exited, shutting down..."
cleanup
