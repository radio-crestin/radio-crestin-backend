#!/bin/sh
# Local cleanup: keep only recent segments (S3 has the 7-day archive)
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"

while true; do
    # Delete local segments older than LOCAL_RETENTION_MINUTES
    # Keep init segments (init-*.m4s) as they're needed for playback
    find /data/segments -name 'chunk-*.m4s' -mmin +"$LOCAL_RETENTION_MINUTES" -delete 2>/dev/null

    # Prune NGINX caches
    find /data/cache -mindepth 1 -type f -mmin +60 -delete 2>/dev/null
    find /data/cache -mindepth 1 -type d -empty -delete 2>/dev/null

    sleep 60
done
