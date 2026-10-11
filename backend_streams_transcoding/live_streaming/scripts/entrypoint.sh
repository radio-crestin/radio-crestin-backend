#!/bin/bash
set -euo pipefail

: "${STATION_SLUG:?STATION_SLUG is required}"
: "${STREAM_URL:?STREAM_URL is required}"

if ! echo "$STATION_SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$'; then
    echo "ERROR: Invalid STATION_SLUG format: $STATION_SLUG"
    exit 1
fi

SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
# Live playlist window served to normal listeners at /index.m3u8. Sized to
# guarantee AT LEAST 10 min (600s) of audio is always available, with margin:
# 660s / 6s = 110 entries → 11 min steady-state. ffmpeg transiently holds a
# few segments fewer than the list size while rotating near the live edge
# (~107 observed at cap), so the 660s target keeps the served window ≥10 min
# even at the worst point of the rotation. The playlist grows to ~20 KB
# (from ~12 KB at the old 65-entry / 6.5-min window); listeners poll it every
# ~6s, so this raises playlist egress ~1.7x — an accepted cost for the DVR-
# grade 10-min live buffer. playlist_rewriter renders index.m3u8 as the newest
# HLS_LIST_SIZE segments of its history; ffmpeg's own live.m3u8 (same size)
# only feeds the rewriter.
HLS_WINDOW_SECONDS="${HLS_WINDOW_SECONDS:-660}"
HLS_LIST_SIZE="${HLS_LIST_SIZE:-$((HLS_WINDOW_SECONDS / SEGMENT_DURATION))}"
# DVR playlist window served at /dvr.m3u8 — apps switch to it only when the
# user rewinds ("seek back up to 1h"). Built by playlist_rewriter.py from
# its segment history: 3600s / 6s = 600 entries.
#
# Retention: ffmpeg deletes nothing (no delete_segments; with it ffmpeg kept
# only about one live window of old files, ~22 min, whatever the threshold).
# The rewriter drops a segment from both playlists once it is older than the
# DVR window + 5 min, and cleanup.sh deletes the file 5 min after that
# (DVR window + 10 min), so a listed segment is never deleted under a
# player. ~700 files ≈ 37 MB at 64k HE-AAC in MPEG-TS — well within the
# per-station 200Mi emptyDir limit set by the stream controller.
# Epoch-prefixed segment names stay globally unique, so long retention is
# safe across ffmpeg restarts (no name collisions).
DVR_WINDOW_SECONDS="${DVR_WINDOW_SECONDS:-3600}"
DVR_LIST_SIZE="${DVR_LIST_SIZE:-$((DVR_WINDOW_SECONDS / SEGMENT_DURATION))}"
# How ffmpeg handles a broken source connection:
#   inprocess  (default) reconnect inside the running ffmpeg. A reconnect
#              burst that replays audio already received leaves the PDT
#              ahead by the replayed length until the next run
#              (PostHog pdt_stamp kind=replay).
#   restart    end the run; ffmpeg_loop starts a new one 2 s later. The
#              rewriter dates each new run exactly and withholds replayed
#              segments, at the cost of one EXT-X-DISCONTINUITY per
#              interruption. Set on the controller once telemetry says so.
FFMPEG_INPUT_RECONNECT="${FFMPEG_INPUT_RECONNECT:-inprocess}"
case "$FFMPEG_INPUT_RECONNECT" in
    inprocess|restart) ;;
    *)
        echo "WARNING: unknown FFMPEG_INPUT_RECONNECT=$FFMPEG_INPUT_RECONNECT, using inprocess"
        FFMPEG_INPUT_RECONNECT=inprocess
        ;;
esac

# Exported so child processes (stream_monitor, playlist_rewriter, cleanup.sh)
# always see the effective values instead of falling back to their own defaults.
export SEGMENT_DURATION HLS_WINDOW_SECONDS HLS_LIST_SIZE
export DVR_WINDOW_SECONDS DVR_LIST_SIZE

echo "Station: $STATION_SLUG"
echo "Stream:  $STREAM_URL"
echo "HLS:     HE-AAC v1 64k, ${SEGMENT_DURATION}s segments, ${HLS_LIST_SIZE} live / ${DVR_LIST_SIZE} DVR entries, input reconnect: ${FFMPEG_INPUT_RECONNECT}"

# shellcheck source=supervisor.sh
. /app/scripts/supervisor.sh

# Fire a pod-startup event so PostHog timelines line up with restarts.
report_event pod_started \
    --prop segment_duration="$SEGMENT_DURATION" \
    --prop hls_list_size="$HLS_LIST_SIZE" \
    --prop dvr_list_size="$DVR_LIST_SIZE" \
    --prop dvr_window_seconds="$DVR_WINDOW_SECONDS" \
    --prop ffmpeg_input_reconnect="$FFMPEG_INPUT_RECONNECT"

# Directory layout:
#   /data/hls/aac/live.m3u8                FFmpeg-managed live playlist
#   /data/hls/aac/${slug}-${boot}-N.ts     FFmpeg-managed segments. The
#                                          ${slug}-${boot} prefix makes
#                                          filenames globally unique across
#                                          stations (slug) and ffmpeg
#                                          restarts (boot epoch); N is the
#                                          per-run counter from ffmpeg.
mkdir -p /data/hls/aac /data/metadata

# Render NGINX config with env vars
envsubst '${STATION_SLUG}' < /app/nginx/nginx.conf > /tmp/nginx/nginx.conf

echo "Starting NGINX..."
nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' &
NGINX_PID=$!

# Every helper runs under `supervise` (supervisor.sh): it is restarted
# whenever it exits, with backoff, and each exit is reported to PostHog
# (helper_exit). SIGTERM to a supervise subshell stops its helper.
HELPER_PIDS=()
start_helper() {   # start_helper NAME CMD...
    echo "Starting $1..."
    supervise "$@" &
    HELPER_PIDS+=($!)
}
start_helper health_server python3 /app/scripts/health_server.py
start_helper metadata_monitor python3 /app/scripts/metadata_monitor.py
start_helper scraper_engine python3 /app/scripts/scraper_engine.py
start_helper playlist_rewriter python3 /app/scripts/playlist_rewriter.py
start_helper log_monitor python3 /app/scripts/log_monitor.py
start_helper stream_monitor python3 /app/scripts/stream_monitor.py
start_helper segment_cleanup sh /app/scripts/cleanup.sh

FFMPEG_LOOP_PID=""
cleanup() {
    echo "Shutting down gracefully..."
    # ffmpeg_loop and each supervise subshell stop their own child on TERM.
    kill -TERM "$FFMPEG_LOOP_PID" "${HELPER_PIDS[@]}" 2>/dev/null || true
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
#   -hls_list_size    — number of segments in live.m3u8 (sliding window;
#                       only playlist_rewriter reads it)
#   -hls_segment_type mpegts   — MPEG-TS container
#   -hls_segment_filename      — segment naming pattern
# No delete_segments: retention is the rewriter's and cleanup.sh's job.
#
FFMPEG_PID=""
if [ "$FFMPEG_INPUT_RECONNECT" = restart ]; then
    # Any read error or 10 s (µs) without data ends the run.
    FFMPEG_INPUT_OPTS=(-rw_timeout 10000000)
else
    # Reconnect in-process; -rw_timeout turns a silent connection into a
    # reconnect after 10 s instead of waiting for the server to reset it
    # (45 s measured) or forever (black-holed TCP).
    FFMPEG_INPUT_OPTS=(
        -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1
        -reconnect_delay_max 4 -rw_timeout 10000000
    )
fi

start_ffmpeg() {
    # Per-invocation segment-name prefix. Three uniqueness layers stack so
    # that no two segments — anywhere on the CDN, ever — share a filename:
    #   ${STATION_SLUG}   — distinguishes one station's pod from another's
    #                       (CDN cache-key collisions between stations).
    #   $(date +%s)       — distinguishes ffmpeg restarts within the same pod
    #                       (counter resets at restart; this prefix doesn't).
    #   %d                — ffmpeg's segment counter (unique within a run;
    #                       seeded from the current epoch via
    #                       hls_start_number_source=epoch, so it's also a
    #                       wallclock-ish number).
    # STATION_SLUG is regex-validated near the top of this script, so it
    # contains only [a-z0-9-] — safe to embed in a path.
    local SEGMENT_PREFIX="${STATION_SLUG}-$(date +%s)"
    echo "Starting FFmpeg (HLS, ${SEGMENT_DURATION}s, ${HLS_LIST_SIZE} segments, prefix=${SEGMENT_PREFIX})..."
    # Mirrors the old backend_hls_streaming flag set:
    #   - HE-AAC v1 64k (libfdk_aac aac_he)        same encoder/bitrate as legacy clients tuned for
    #   - hls_flags program_date_time              ffmpeg's PDT (muxer start + media time) stays in
    #                                              live.m3u8 for diagnosis only; playlist_rewriter
    #                                              stamps wall-clock PDT itself
    #   - hls_start_number_source epoch            the first MEDIA-SEQUENCE of a pod = wallclock
    #                                              seconds, so it advances across pod replacements;
    #                                              within a pod the rewriter keeps it contiguous
    #   - abort_on empty_output_stream             die fast on persistent input loss; bash
    #                                              ffmpeg_loop restarts with backoff
    # Kept from the new pipeline (improvements over legacy):
    #   - +temp_file                               atomic writes: a segment's mtime is when its
    #                                              last sample arrived (the rewriter's clock)
    #   - ${slug}-${boot}-%d.ts                    counter naming, prefixed
    #                                              per-station + per-restart so segments stay
    #                                              globally unique on a shared CDN. Replaces
    #                                              the previous `-strftime 1 %s.ts` scheme,
    #                                              which collided whenever two segments wrote
    #                                              in the same epoch second.
    #   - FFMPEG_INPUT_OPTS                        input reconnect policy (FFMPEG_INPUT_RECONNECT)
    ffmpeg -loglevel warning \
        "${FFMPEG_INPUT_OPTS[@]}" \
        -fflags +genpts+discardcorrupt -max_delay 5000000 \
        -i "$STREAM_URL" -y \
        -map 0:a:0 -c:a libfdk_aac -profile:a aac_he -b:a 64k \
        -flags +global_header -async 1 -ac 2 -ar 44100 \
        -bufsize 30000000 -sc_threshold 0 \
        -abort_on empty_output_stream \
        -f hls \
            -hls_init_time "$SEGMENT_DURATION" \
            -hls_time "$SEGMENT_DURATION" \
            -hls_list_size "$HLS_LIST_SIZE" \
            -hls_flags independent_segments+split_by_time+program_date_time+omit_endlist+temp_file \
            -hls_start_number_source epoch \
            -hls_segment_type mpegts \
            -hls_segment_options 'mpegts_flags=+initial_discontinuity' \
            -hls_segment_filename "/data/hls/aac/${SEGMENT_PREFIX}-%d.ts" \
            '/data/hls/aac/live.m3u8' &
    FFMPEG_PID=$!
    echo "FFmpeg started (PID $FFMPEG_PID)"
}

ffmpeg_loop &
FFMPEG_LOOP_PID=$!

# Wait for any critical background process to exit
wait -n "$NGINX_PID" || true
echo "Critical process exited, shutting down..."
cleanup
