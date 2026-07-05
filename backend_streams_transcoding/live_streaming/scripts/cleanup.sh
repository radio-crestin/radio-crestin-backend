#!/bin/sh
# FFmpeg's -hls_flags delete_segments handles normal cleanup.
# This script is a safety net for orphaned segments after FFmpeg restarts
# (epoch-named segments from old sessions won't be tracked by the new FFmpeg).
# Also sweeps any leftover .pdt sidecars from the previous playlist_generator
# implementation (PDT now comes from ffmpeg directly, no sidecars are written).
#
# The sweep age is derived from the serving window so it can never delete a
# segment that is still referenced by the live playlist:
#   (HLS_LIST_SIZE + HLS_DELETE_THRESHOLD) x SEGMENT_DURATION + 10 min margin.
# Defaults mirror entrypoint.sh: (600+100)x6s/60 + 10 = 80 minutes.
SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
HLS_LIST_SIZE="${HLS_LIST_SIZE:-600}"
HLS_DELETE_THRESHOLD="${HLS_DELETE_THRESHOLD:-100}"
RETENTION_MIN=$(( (HLS_LIST_SIZE + HLS_DELETE_THRESHOLD) * SEGMENT_DURATION / 60 + 10 ))

while true; do
    find /data/hls/aac -name '*.ts' -mmin +"$RETENTION_MIN" -delete 2>/dev/null
    find /data/hls/aac -name '*.pdt' -delete 2>/dev/null
    sleep 60
done
