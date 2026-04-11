#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

RETENTION_DAYS="${RETENTION_DAYS:-7}"
SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"

export SEGMENT_DURATION

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "HLS:     AAC+ 64k + Opus 48k"
echo "S3:      ${S3_BUCKET:-disabled}"

# Directory layout:
#   /data/hls/aac/live.m3u8              FFmpeg AAC+ playlist
#   /data/hls/aac/segments/<epoch>.ts    HE-AAC 64k segments
#   /data/hls/opus/live.m3u8             FFmpeg Opus playlist
#   /data/hls/opus/segments/<epoch>.m4s  Opus 64k fMP4 segments
#   /data/hls/opus/init.mp4              Opus init segment
mkdir -p /data/hls/aac/segments /data/hls/opus/segments /data/cache/playlist /data/cache/s3

# Record pod start time for gap tracking
date +%s > /data/pod_started_at

# Render NGINX config with env vars
export S3_BUCKET="${S3_BUCKET:-}"
export S3_ENDPOINT="${S3_ENDPOINT:-}"
envsubst '${STATION_SLUG} ${S3_BUCKET} ${S3_ENDPOINT}' < /app/nginx/nginx.conf > /tmp/nginx/nginx.conf

echo "Starting NGINX..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

echo "Starting playlist generator..."
python3 /app/scripts/playlist_generator.py &
PLAYLIST_PID=$!

echo "Starting S3 uploader..."
python3 /app/scripts/s3_uploader.py &
S3_PID=$!

echo "Starting health server..."
python3 /app/scripts/health_server.py &
HEALTH_PID=$!

echo "Starting metadata monitor..."
python3 /app/scripts/metadata_monitor.py &
METADATA_PID=$!

echo "Starting ID3 injector..."
python3 /app/scripts/id3_injector.py &
ID3_PID=$!

echo "Starting cleanup..."
/app/scripts/cleanup.sh &
CLEANUP_PID=$!

cleanup() {
    echo "Shutting down gracefully..."
    # 1. Stop FFmpeg (stop producing new segments)
    kill -TERM "$FFMPEG_PID" 2>/dev/null || true
    # 2. Stop metadata monitor
    kill -TERM "$METADATA_PID" "$ID3_PID" "$CLEANUP_PID" 2>/dev/null || true
    # 3. Final S3 sync — upload remaining segments + metadata before dying
    echo "Final S3 sync..."
    python3 -c "
import sys; sys.path.insert(0, '/app/scripts')
from s3_uploader import sync_all, write_s3_index, upload_file, upload_bytes, STATION_SLUG
try:
    sync_all()
    write_s3_index()
    # Upload metadata to S3
    import os, glob
    for f in glob.glob('/data/metadata/**/*.json', recursive=True):
        key = STATION_SLUG + '/metadata/' + os.path.relpath(f, '/data/metadata')
        upload_file(f, key)
    print('Final S3 sync complete', flush=True)
except Exception as e:
    print(f'Final S3 sync error: {e}', flush=True)
" 2>/dev/null || true
    # 4. Kill health server so readiness probe fails
    kill -TERM "$HEALTH_PID" 2>/dev/null || true
    # 5. Keep NGINX alive to serve cached/S3 segments for in-flight requests
    sleep 5
    # 6. Stop NGINX and playlist generator
    kill -TERM "$S3_PID" "$NGINX_PID" "$PLAYLIST_PID" 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── FFmpeg: dual HLS (AAC+ .ts + Opus fMP4) ──
# AAC+: HE-AAC 64k in .ts — universal compatibility (Safari, all browsers)
# Opus: Opus 64k in fMP4 — better quality, supported by hls.js / Chrome / Firefox
echo "Starting FFmpeg..."
ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_delay_max 30 \
    -i "$STREAM_URL" -y \
    -map 0:a:0 -c:a libfdk_aac -profile:a aac_he -b:a 64k -ac 2 -ar 44100 \
    -f hls \
        -hls_time "$SEGMENT_DURATION" \
        -hls_list_size 0 \
        -hls_flags split_by_time+program_date_time+omit_endlist \
        -hls_start_number_source epoch \
        -hls_segment_filename '/data/hls/aac/segments/%d.ts' \
        /data/hls/aac/live.m3u8 \
    -map 0:a:0 -c:a libopus -b:a 48k -ac 2 -ar 48000 \
        -application audio -vbr on -compression_level 10 -frame_duration 20 \
    -f hls \
        -hls_time "$SEGMENT_DURATION" \
        -hls_list_size 0 \
        -hls_segment_type fmp4 \
        -hls_fmp4_init_filename init.mp4 \
        -hls_flags split_by_time+program_date_time+omit_endlist \
        -hls_start_number_source epoch \
        -hls_segment_filename '/data/hls/opus/segments/%d.m4s' \
        /data/hls/opus/live.m3u8 &
FFMPEG_PID=$!

echo "FFmpeg started (PID $FFMPEG_PID)"
wait -n "$FFMPEG_PID" "$NGINX_PID" "$PLAYLIST_PID" || true
echo "Process exited, shutting down..."
cleanup
