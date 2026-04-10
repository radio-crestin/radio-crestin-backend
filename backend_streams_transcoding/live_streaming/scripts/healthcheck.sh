#!/bin/sh
# Check that DASH manifest exists and is recent (< 60s)
DASH=/data/manifest.mpd
[ -f "$DASH" ] || exit 1
age=$(($(date +%s) - $(stat -c %Y "$DASH" 2>/dev/null || stat -f %m "$DASH")))
[ "$age" -lt 60 ] || exit 1

# Check that segments exist
ls /data/segments/chunk-*.m4s >/dev/null 2>&1 || exit 1

# Check NGINX responds
wget -q -O /dev/null http://localhost:8080/health || exit 1

# Check playlist generator responds
wget -q -O /dev/null http://localhost:8081/index.m3u8 || exit 1

exit 0
