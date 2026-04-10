#!/bin/sh
# Check DASH manifest is fresh
[ -f /data/dash/manifest.mpd ] || exit 1
age=$(($(date +%s) - $(stat -c %Y /data/dash/manifest.mpd 2>/dev/null || stat -f %m /data/dash/manifest.mpd)))
[ "$age" -lt 60 ] || exit 1
# Check HLS segments exist
ls /data/hls/segments/*.ts >/dev/null 2>&1 || exit 1
# Check NGINX
wget -q -O /dev/null http://localhost:8080/health || exit 1
# Check playlist generator
wget -q -O /dev/null http://localhost:8081/index.m3u8 || exit 1
exit 0
