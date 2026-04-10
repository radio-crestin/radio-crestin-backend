#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

RETENTION_DAYS="${RETENTION_DAYS:-7}"
OPUS_BITRATE_LOW="${OPUS_BITRATE_LOW:-48k}"
OPUS_BITRATE_HIGH="${OPUS_BITRATE_HIGH:-96k}"
SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"

export SEGMENT_DURATION

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "Opus:    ${OPUS_BITRATE_LOW} / ${OPUS_BITRATE_HIGH}"
echo "S3:      ${S3_BUCKET:-disabled}"

# Directory layout:
#   /data/dash/manifest.mpd          DASH manifest
#   /data/dash/0/init.m4s + chunks   Opus 32k segments
#   /data/dash/1/init.m4s + chunks   Opus 96k segments
#   /data/hls/live.m3u8              FFmpeg HLS playlist
#   /data/hls/segments/<epoch>.ts    AAC 64k segments
mkdir -p /data/dash/0 /data/dash/1 /data/hls/segments /data/cache/playlist /data/cache/s3

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

echo "Starting DASH patcher..."
python3 /app/scripts/dash_patcher.py &
DASH_PID=$!

echo "Starting S3 uploader..."
python3 /app/scripts/s3_uploader.py &
S3_PID=$!

echo "Starting cleanup..."
/app/scripts/cleanup.sh &
CLEANUP_PID=$!

cleanup() {
    echo "Shutting down..."
    kill -TERM "$FFMPEG_PID" "$NGINX_PID" "$PLAYLIST_PID" "$DASH_PID" "$S3_PID" "$CLEANUP_PID" 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ── FFmpeg: DASH (Opus) + HLS (AAC) ──
# DASH: 2 Opus qualities in fMP4 (for dash.js / Shaka Player)
# HLS:  AAC 64k in .ts (for hls.js / Safari — Opus fMP4 not supported)
echo "Starting FFmpeg..."
ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 30 \
    -i "$STREAM_URL" -y \
    -map 0:a:0 -c:a:0 libopus -b:a:0 "$OPUS_BITRATE_LOW" -ac 2 -ar 48000 \
    -map 0:a:0 -c:a:1 libopus -b:a:1 "$OPUS_BITRATE_HIGH" -ac 2 -ar 48000 \
    -f dash \
        -seg_duration "$SEGMENT_DURATION" \
        -frag_duration 2 \
        -window_size 0 \
        -extra_window_size 0 \
        -remove_at_exit 0 \
        -streaming 1 \
        -use_timeline 1 \
        -use_template 1 \
        -utc_timing_url "https://time.akamai.com/?iso" \
        -adaptation_sets "id=0,streams=0,1" \
        -format_options "movflags=+cmaf" \
        -media_seg_name '$RepresentationID$/chunk-$Number%09d$.m4s' \
        -init_seg_name '$RepresentationID$/init.m4s' \
        /data/dash/manifest.mpd \
    -map 0:a:0 -c:a aac -profile:a aac_low -b:a 64k -ac 2 -ar 44100 \
    -f hls \
        -hls_time "$SEGMENT_DURATION" \
        -hls_list_size 0 \
        -hls_flags independent_segments+split_by_time+program_date_time+omit_endlist \
        -hls_start_number_source epoch \
        -hls_segment_filename '/data/hls/segments/%d.ts' \
        /data/hls/live.m3u8 &
FFMPEG_PID=$!

echo "FFmpeg started (PID $FFMPEG_PID)"
wait -n "$FFMPEG_PID" "$NGINX_PID" "$PLAYLIST_PID" || true
echo "Process exited, shutting down..."
cleanup
