#!/bin/sh
# FFmpeg's -hls_flags delete_segments handles normal cleanup.
# This script is a safety net for orphaned segments after FFmpeg restarts
# (epoch-named segments from old sessions won't be tracked by the new FFmpeg).
# Also sweeps any leftover .pdt sidecars from the previous playlist_generator
# implementation (PDT now comes from ffmpeg directly, no sidecars are written).
while true; do
    find /data/hls/aac -name '*.ts' -mmin +30 -delete 2>/dev/null
    find /data/hls/aac -name '*.pdt' -delete 2>/dev/null
    sleep 60
done
