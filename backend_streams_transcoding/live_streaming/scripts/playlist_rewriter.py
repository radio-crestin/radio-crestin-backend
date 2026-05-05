"""
HLS playlist rewriter — copies ffmpeg's live.m3u8 to index.m3u8, injecting
EXT-X-DATERANGE song-metadata tags from /data/metadata/index.json.

Why a separate file instead of rewriting in place:
  - ffmpeg writes live.m3u8 via temp-file + atomic rename (`+temp_file`); we
    don't fight that. We read the whole file (always intact thanks to the
    rename), produce the enhanced version, and atomic-rename our own output.
  - nginx serves the enhanced file *statically* — no proxy_pass to Python,
    no per-request cost, no Python becoming a single point of failure for
    playlist availability. If the rewriter falls behind, nginx just keeps
    serving the last good index.m3u8.

EXT-X-DATERANGE was added in HLS v6 (RFC 8216 §4.4.5.1), so when we inject
any DATERANGE entry we also bump #EXT-X-VERSION:3 → #EXT-X-VERSION:6. ffmpeg
otherwise writes v3.

DATERANGE attributes are intentionally minimal — only ID, START-DATE, and
X-* custom attrs. Per AVPlayer's HLS metadata behavior, CLASS / DURATION /
END-DATE are load-bearing playback markers (interstitial cues, hard-end
boundaries) and can mis-handle live audio when the player treats a
metadata range as a playback boundary.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

FFMPEG_PLAYLIST = Path("/data/hls/aac/live.m3u8")
ENHANCED_PLAYLIST = Path("/data/hls/aac/index.m3u8")
METADATA_PATH = Path("/data/metadata/index.json")

POLL_INTERVAL = 1
SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
HLS_LIST_SIZE = int(os.environ.get("HLS_LIST_SIZE", "65"))


SEGMENT_PREFIXES = (
    "#EXTINF",
    "#EXT-X-PROGRAM-DATE-TIME",
    "#EXT-X-BYTERANGE",
    "#EXT-X-DISCONTINUITY",
    "#EXT-X-KEY",
    "#EXT-X-MAP",
)


def _epoch_to_pdt(epoch: float) -> str:
    """ISO-8601 UTC with millisecond precision — matches the format
    AVPlayer's metadata collector expects on START-DATE."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z", t)


def _load_songs() -> list[dict]:
    try:
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    songs = list(data.get("recent", []))
    cur = data.get("current")
    if cur and cur.get("raw"):
        songs.append(cur)
    songs.sort(key=lambda s: s.get("started_at", 0))
    return songs


def _daterange_for_song(song: dict) -> str | None:
    started_at = song.get("started_at", 0)
    if not started_at:
        return None
    title = (song.get("title") or song.get("raw") or "").replace('"', "'")
    artist = (song.get("artist") or "").replace('"', "'")
    if not title and not artist:
        return None
    thumbnail = (song.get("thumbnail_url") or "").replace('"', "'")
    song_id = song.get("song_id")
    station_id = song.get("station_id")

    # Stable, unique ID: prefer backend song_id (immutable, globally unique)
    # else fall back to the epoch start (unique per song instance on the
    # station). Reusing slot-style IDs would cause AVPlayer to reprocess the
    # range when attributes change.
    uid = f"song-{song_id}-{int(started_at)}" if song_id else f"song-{int(started_at)}"

    parts = [
        f'ID="{uid}"',
        f'START-DATE="{_epoch_to_pdt(started_at)}"',
        f'X-TITLE="{title}"',
        f'X-ARTIST="{artist}"',
    ]
    if thumbnail:
        parts.append(f'X-THUMBNAIL-URL="{thumbnail}"')
    if song_id:
        parts.append(f'X-SONG-ID="{song_id}"')
    if station_id:
        parts.append(f'X-STATION-ID="{station_id}"')
    return "#EXT-X-DATERANGE:" + ",".join(parts)


def _earliest_segment_pdt_epoch(raw: str) -> float | None:
    """Extract the smallest EXT-X-PROGRAM-DATE-TIME from the playlist as a
    Unix epoch. None if no PDT lines are present."""
    earliest: float | None = None
    for line in raw.split("\n"):
        if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            ts = line[len("#EXT-X-PROGRAM-DATE-TIME:"):].strip()
            try:
                # Tolerate both `+0000` and `Z` UTC suffixes
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                dt = datetime.fromisoformat(ts)
                ep = dt.astimezone(timezone.utc).timestamp()
                if earliest is None or ep < earliest:
                    earliest = ep
            except (ValueError, TypeError):
                continue
    return earliest


def enhance(raw: str, songs: list[dict]) -> str:
    """Return the playlist with DATERANGE tags injected into the header
    block (between EXT-X-MEDIA-SEQUENCE and the first segment), and the
    version bumped to 6 if any DATERANGE was added.

    Per RFC 8216 §4.4.5.1, EXT-X-DATERANGE applies to the entire playlist;
    its physical position has no impact on which segment it 'belongs to'.
    Putting them in the header block keeps AVPlayer from treating each tag
    as a per-segment playback boundary.

    Cutoff is the earliest segment's PROGRAM-DATE-TIME (with a 2s grace),
    not wall-clock. Apple's mediastreamvalidator flags a DATERANGE that
    disappears while its time range still overlaps any segment in the
    playlist ("Removed an EXT-X-DATERANGE while mapped to range in
    playlist"). Tying the cutoff to the playlist content guarantees a
    DATERANGE only drops once the playlist has rolled past it.

    The most recent song (by START-DATE) is always kept, even if it
    started before the earliest segment — for a long-running song whose
    start scrolled out of the playlist window, AVPlayer still needs the
    DATERANGE to show "now playing".
    """
    earliest_pdt = _earliest_segment_pdt_epoch(raw)
    if earliest_pdt is None:
        # No PDT lines yet (warmup); fall back to keeping all recent songs.
        cutoff = 0.0
    else:
        cutoff = earliest_pdt - 2

    most_recent_started_at = max(
        (s.get("started_at", 0) for s in songs), default=0
    )

    daterange_lines: list[str] = []
    seen: set[str] = set()
    for song in songs:
        started_at = song.get("started_at", 0)
        # Drop entries whose range is entirely behind the playlist window,
        # except always keep the single most-recent song so AVPlayer can
        # render "now playing" for long-running songs.
        if started_at < cutoff and started_at != most_recent_started_at:
            continue
        line = _daterange_for_song(song)
        if not line:
            continue
        m = re.match(r'#EXT-X-DATERANGE:ID="([^"]+)"', line)
        if m:
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
        daterange_lines.append(line)

    if not daterange_lines:
        return raw

    out: list[str] = []
    inserted = False
    for line in raw.rstrip("\n").split("\n"):
        if line.startswith("#EXT-X-VERSION:"):
            out.append("#EXT-X-VERSION:6")
            continue
        if not inserted:
            stripped = line.lstrip()
            if stripped.endswith(".ts") or stripped.startswith(SEGMENT_PREFIXES):
                out.extend(daterange_lines)
                inserted = True
        out.append(line)

    if not inserted:
        out.extend(daterange_lines)
    return "\n".join(out) + "\n"


def write_atomic(path: Path, content: str) -> None:
    """Atomic write: tmp + os.replace. nginx never serves a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def main() -> None:
    print(f"playlist_rewriter: {FFMPEG_PLAYLIST} → {ENHANCED_PLAYLIST}", flush=True)
    last_playlist_mtime = 0.0
    last_metadata_mtime = 0.0
    while True:
        try:
            playlist_stat = FFMPEG_PLAYLIST.stat()
        except FileNotFoundError:
            time.sleep(POLL_INTERVAL)
            continue
        try:
            metadata_mtime = METADATA_PATH.stat().st_mtime
        except FileNotFoundError:
            metadata_mtime = 0.0

        if (playlist_stat.st_mtime != last_playlist_mtime
                or metadata_mtime != last_metadata_mtime):
            try:
                with open(FFMPEG_PLAYLIST, "r") as f:
                    raw = f.read()
                if raw and "#EXTM3U" in raw:
                    songs = _load_songs()
                    write_atomic(ENHANCED_PLAYLIST, enhance(raw, songs))
                    last_playlist_mtime = playlist_stat.st_mtime
                    last_metadata_mtime = metadata_mtime
            except Exception as e:
                print(f"playlist_rewriter: error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
