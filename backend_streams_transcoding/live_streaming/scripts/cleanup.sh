#!/bin/sh
# Segment retention. ffmpeg deletes nothing (no delete_segments), so this
# sweep is the only thing that removes segment files.
#
# playlist_rewriter drops a segment from both playlists once it is older
# than the DVR window + 5 min; this sweep deletes the file 5 min after that
# (DVR window + 10 min, by mtime). A player that fetched a playlist just
# before a segment left it can therefore still download that segment, and
# no listed URI ever 404s. Defaults mirror entrypoint.sh: 3600 s / 60 + 10
# = 70 minutes, ~700 files.
DVR_WINDOW_SECONDS="${DVR_WINDOW_SECONDS:-3600}"
RETENTION_MIN=$(( DVR_WINDOW_SECONDS / 60 + 10 ))

while true; do
    find /data/hls/aac -name '*.ts' -mmin +"$RETENTION_MIN" -delete 2>/dev/null
    sleep 60
done
