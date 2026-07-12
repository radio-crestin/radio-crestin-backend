#!/bin/sh
# FFmpeg's -hls_flags delete_segments handles normal cleanup.
# This script is a safety net for orphaned segments after FFmpeg restarts
# (epoch-named segments from old sessions won't be tracked by the new FFmpeg).
# Also sweeps any leftover .pdt sidecars from the previous playlist_generator
# implementation (PDT now comes from ffmpeg directly, no sidecars are written).
#
# The sweep age is derived from the on-disk retention window — the live list
# plus ffmpeg's delete threshold, which is sized to cover the larger DVR
# window (dvr.m3u8) — so it can never delete a segment still referenced by
# either playlist:
#   (HLS_LIST_SIZE + HLS_DELETE_THRESHOLD) x SEGMENT_DURATION + 10 min margin.
# Defaults mirror entrypoint.sh: (110+590)x6s/60 + 10 = 80 minutes. (The
# on-disk total is DVR-driven, so it stays 700 segments regardless of the
# live-window size — widening the live window does not shorten retention.)
SEGMENT_DURATION="${SEGMENT_DURATION:-6}"
HLS_LIST_SIZE="${HLS_LIST_SIZE:-110}"
HLS_DELETE_THRESHOLD="${HLS_DELETE_THRESHOLD:-590}"
RETENTION_MIN=$(( (HLS_LIST_SIZE + HLS_DELETE_THRESHOLD) * SEGMENT_DURATION / 60 + 10 ))

while true; do
    find /data/hls/aac -name '*.ts' -mmin +"$RETENTION_MIN" -delete 2>/dev/null
    find /data/hls/aac -name '*.pdt' -delete 2>/dev/null
    sleep 60
done
