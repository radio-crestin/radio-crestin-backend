#!/bin/sh
# Hourly cleanup of old segments and stale cache
while true; do
    # Delete HLS and DASH segments older than RETENTION_DAYS
    find /data/hls/segments -name '*.ts' -mtime +"${RETENTION_DAYS:-7}" -delete 2>/dev/null
    find /data/dash -name '*.m4s' -mtime +"${RETENTION_DAYS:-7}" -delete 2>/dev/null

    # Prune NGINX playlist cache entries older than retention period
    # (NGINX also self-manages via max_size and inactive, this is a safety net)
    find /data/cache/playlist -type f -mtime +"${RETENTION_DAYS:-7}" -delete 2>/dev/null
    # Remove empty cache hash directories left behind
    find /data/cache/playlist -mindepth 1 -type d -empty -delete 2>/dev/null

    sleep 3600
done
