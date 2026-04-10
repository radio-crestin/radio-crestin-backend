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
OPUS_BITRATE_HIGH="${OPUS_BITRATE_HIGH:-64k}"
HLS_SEGMENT_DURATION="${HLS_SEGMENT_DURATION:-6}"

export HLS_SEGMENT_DURATION

echo "Starting live streaming for station: $STATION_SLUG"
echo "Stream URL: $STREAM_URL"
echo "Retention: ${RETENTION_DAYS} days"
echo "HLS segment duration: ${HLS_SEGMENT_DURATION}s"
echo "DASH qualities: ${OPUS_BITRATE_LOW} / ${OPUS_BITRATE_HIGH}"

# Ensure data directories exist
# segments/ subfolder keeps .ts files separate from FFmpeg's live.m3u8
# cache/playlist/ stores NGINX proxy cache for timestamped playlists
mkdir -p /data/hls/segments /data/dash /data/cache/playlist

# Start NGINX in background
echo "Starting NGINX..."
nginx -c /app/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

# Start dynamic HLS playlist generator in background
echo "Starting playlist generator..."
python3 /app/scripts/playlist_generator.py &
PLAYLIST_PID=$!

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
    kill -TERM "$CLEANUP_PID" 2>/dev/null || true
    wait
    echo "All processes stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# Start FFmpeg with dual output (HLS + DASH multi-bitrate)
# HLS: segments named by epoch timestamp in /data/hls/segments/
# DASH: segments in /data/dash/
# Segment deletion is handled by cleanup.sh (7-day TTL), not FFmpeg
echo "Starting FFmpeg..."
ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30 \
    -i "$STREAM_URL" -y \
    -map 0:a:0 -c:a:0 libopus -b:a:0 "$OPUS_BITRATE_LOW" -ac 2 -ar 48000 \
    -map 0:a:0 -c:a:1 libopus -b:a:1 "$OPUS_BITRATE_HIGH" -ac 2 -ar 48000 \
    -f dash \
        -seg_duration "$HLS_SEGMENT_DURATION" \
        -window_size 0 \
        -extra_window_size 0 \
        -remove_at_exit 0 \
        -use_timeline 1 \
        -use_template 1 \
        -utc_timing_url "https://time.akamai.com/?iso" \
        -adaptation_sets "id=0,streams=0,1" \
        -media_seg_name 'chunk-stream$RepresentationID$-$Number%09d$.m4s' \
        -init_seg_name 'init-stream$RepresentationID$.m4s' \
        /data/dash/manifest.mpd \
    -map 0:a:0 -c:a aac -profile:a aac_low -b:a 64k -ac 2 -ar 44100 \
    -f hls \
        -hls_time "$HLS_SEGMENT_DURATION" \
        -hls_list_size 0 \
        -hls_flags independent_segments+split_by_time+program_date_time+omit_endlist \
        -hls_start_number_source epoch \
        -hls_segment_filename '/data/hls/segments/%d.ts' \
        /data/hls/live.m3u8 &
FFMPEG_PID=$!

echo "FFmpeg started with PID $FFMPEG_PID"

# Wait for any child to exit
wait -n "$FFMPEG_PID" "$NGINX_PID" "$PLAYLIST_PID" || true

echo "A process exited unexpectedly, shutting down..."
cleanup
