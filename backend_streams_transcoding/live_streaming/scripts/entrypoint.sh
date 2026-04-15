#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
HLS_LIST_SIZE="${HLS_LIST_SIZE:-50}"

export SEGMENT_DURATION

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "HLS:     AAC+ 64k, ${SEGMENT_DURATION}s segments, ${HLS_LIST_SIZE} in playlist"

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

echo "Starting log monitor..."
python3 /app/scripts/log_monitor.py &
LOG_MONITOR_PID=$!

echo "Starting segment cleanup (30min max)..."
sh /app/scripts/cleanup.sh &
CLEANUP_PID=$!

cleanup() {
    echo "Shutting down gracefully..."
    kill -TERM "$FFMPEG_LOOP_PID" 2>/dev/null || true
    kill -TERM "$FFMPEG_PID" 2>/dev/null || true
    kill -TERM "$METADATA_PID" "$ID3_PID" "$SCRAPER_PID" "$MEL_PID" "$LOG_MONITOR_PID" "$CLEANUP_PID" 2>/dev/null || true
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
    ffmpeg -loglevel warning -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_delay_max 30 \
        -i "$STREAM_URL" -y \
        -map 0:a:0 -c:a libfdk_aac -profile:a aac_he -b:a 64k -ac 2 -ar 44100 \
        -f hls \
            -hls_time "$SEGMENT_DURATION" \
            -hls_list_size "$HLS_LIST_SIZE" \
            -hls_flags delete_segments \
            -hls_segment_type mpegts \
            -strftime 1 \
            -hls_segment_filename '/data/hls/aac/%s.ts' \
            '/data/hls/aac/live.m3u8' &
    FFMPEG_PID=$!
    echo "FFmpeg started (PID $FFMPEG_PID)"
}

ffmpeg_loop() {
    local delay=$FFMPEG_RETRY_DELAY
    while true; do
        start_ffmpeg
        wait "$FFMPEG_PID" || true
        echo "FFmpeg exited, retrying in ${delay}s..."
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
