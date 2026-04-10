#!/bin/bash
set -euo pipefail

# Validate required env vars
: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

# Validate slug format (lowercase alphanumeric + hyphens only)
if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

RETENTION_DAYS="${RETENTION_DAYS:-7}"
OPUS_BITRATE_LOW="${OPUS_BITRATE_LOW:-32k}"
OPUS_BITRATE_HIGH="${OPUS_BITRATE_HIGH:-96k}"
SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"

export SEGMENT_DURATION

echo "Starting live streaming for station: $STATION_SLUG"
echo "Stream URL: $STREAM_URL"
echo "Retention: ${RETENTION_DAYS} days (local: ${LOCAL_RETENTION_MINUTES} min)"
echo "Segment duration: ${SEGMENT_DURATION}s"
echo "Opus qualities: ${OPUS_BITRATE_LOW} / ${OPUS_BITRATE_HIGH}"
echo "S3: ${S3_BUCKET:-disabled}"

# Ensure data directories exist
# Single segments/ dir for shared fMP4 segments (used by both DASH and HLS)
mkdir -p /data/segments /data/cache/playlist /data/cache/s3

# Render NGINX config with env vars
export S3_BUCKET="${S3_BUCKET:-}"
export S3_ENDPOINT="${S3_ENDPOINT:-}"
envsubst '${STATION_SLUG} ${S3_BUCKET} ${S3_ENDPOINT}' < /app/nginx/nginx.conf > /tmp/nginx/nginx.conf

# Start NGINX in background
echo "Starting NGINX..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

# Start dynamic playlist generator (creates both HLS m3u8 and serves DASH mpd)
echo "Starting playlist generator..."
python3 /app/scripts/playlist_generator.py &
PLAYLIST_PID=$!

# Start S3 uploader in background
echo "Starting S3 uploader..."
python3 /app/scripts/s3_uploader.py &
S3_PID=$!

# Start cleanup loop in background
echo "Starting cleanup loop..."
/app/scripts/cleanup.sh &
CLEANUP_PID=$!

# Trap SIGTERM/SIGINT and forward to children
cleanup() {
    echo "Received shutdown signal, stopping processes..."
    kill -TERM "$FFMPEG_PID" 2>/dev/null || true
    kill -TERM "$NGINX_PID" 2>/dev/null || true
    kill -TERM "$PLAYLIST_PID" 2>/dev/null || true
    kill -TERM "$S3_PID" 2>/dev/null || true
    kill -TERM "$CLEANUP_PID" 2>/dev/null || true
    wait
    echo "All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── FFmpeg: single DASH output with 2 Opus qualities ──
# Both DASH and HLS share the same fMP4 segments.
# Playlist generator creates HLS playlists from DASH segment data.
echo "Starting FFmpeg..."
ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30 \
    -i "$STREAM_URL" -y \
    -map 0:a:0 -c:a:0 libopus -b:a:0 "$OPUS_BITRATE_LOW" -ac 2 -ar 48000 \
    -map 0:a:0 -c:a:1 libopus -b:a:1 "$OPUS_BITRATE_HIGH" -ac 2 -ar 48000 \
    -f dash \
        -seg_duration "$SEGMENT_DURATION" \
        -window_size 0 \
        -extra_window_size 0 \
        -remove_at_exit 0 \
        -use_timeline 1 \
        -use_template 1 \
        -utc_timing_url "https://time.akamai.com/?iso" \
        -adaptation_sets "id=0,streams=0 id=1,streams=1" \
        -media_seg_name 'segments/chunk-$RepresentationID$-$Number%09d$.m4s' \
        -init_seg_name 'segments/init-$RepresentationID$.m4s' \
        /data/manifest.mpd &
FFMPEG_PID=$!

echo "FFmpeg started with PID $FFMPEG_PID"

# Wait for any child to exit
wait -n "$FFMPEG_PID" "$NGINX_PID" "$PLAYLIST_PID" || true

echo "A process exited unexpectedly, shutting down..."
cleanup
