#!/bin/sh
LOCAL_RETENTION_MINUTES="${LOCAL_RETENTION_MINUTES:-10}"
while true; do
    # HLS AAC segments
    find /data/hls/aac/segments -name '*.ts' -mmin +"$LOCAL_RETENTION_MINUTES" -delete 2>/dev/null
    sleep 60
done
