#!/bin/sh
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"
while true; do
    # HLS AAC segments
    find /data/hls/aac/segments -name '*.ts' -mmin +"$LOCAL_RETENTION_MINUTES" -delete 2>/dev/null
    # NGINX caches
    find /data/cache -type f -mmin +60 -delete 2>/dev/null
    find /data/cache -mindepth 1 -type d -empty -delete 2>/dev/null
    sleep 60
done
