#!/bin/sh
# FFmpeg's -hls_flags delete_segments handles normal cleanup.
# This script is a safety net for orphaned segments after FFmpeg restarts.
while true; do
    find /data/hls/aac -name '*.ts' -mmin +15 -delete 2>/dev/null
    sleep 60
done
