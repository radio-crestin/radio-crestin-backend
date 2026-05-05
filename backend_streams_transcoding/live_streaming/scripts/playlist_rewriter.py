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


def _daterange_for_song(song: dict, end_at: float) -> str | None:
    """Build an EXT-X-DATERANGE line for a song whose end is known.

    `end_at` is the successor song's START-DATE. We only call this for
    songs that have a successor — i.e., songs whose airtime has ended in
    the live source — never for the current song. Reasons:

    * RFC 8216 §4.4.5.1.1 forbids changing any attribute of a published
      DATERANGE. If we emit the current song without END-DATE and then
      add END-DATE once a successor arrives, that's an attribute
      mutation. The previous "successor-aware" rewrite (a6f082f) hit
      this and AVPlayer's validator flagged
      "Removed an EXT-X-DATERANGE while mapped to range in playlist".
    * A DATERANGE without DURATION / END-DATE / END-ON-NEXT has unknown
      duration per the same section — AVPlayer's metadata collector
      treats it as unbounded forward, so removing it is also a violation.

    The cleanest fix in a *livestream* setting (where we don't know the
    song's end until the next one starts) is to defer DATERANGE
    emission until the song has ended. Latest song's metadata still
    reaches clients via PROGRAM-DATE-TIME + the REST poll the mobile
    app already runs every 10s.
    """
    started_at = song.get("started_at", 0)
    if not started_at:
        return None
    if end_at <= started_at:
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
        f'END-DATE="{_epoch_to_pdt(end_at)}"',
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

    DATERANGE emission rules (livestream-aware):

    * Only emit DATERANGE for songs that have ENDED — i.e. songs with a
      successor in the metadata buffer. END-DATE is the successor's
      START-DATE, computed once and never mutated. The CURRENT song gets
      no DATERANGE because we don't know its end until it's superseded;
      committing an end-date now would either lock in a wrong value or
      force us to mutate the tag later (RFC 8216 §4.4.5.1.1 forbids
      changing a published DATERANGE's attributes).

    * Drop a DATERANGE only when its END-DATE is strictly before the
      earliest segment's PROGRAM-DATE-TIME (with a 2s grace) — i.e. its
      time range no longer overlaps any segment in the playlist. Apple's
      mediastreamvalidator flags any earlier removal as
      "Removed an EXT-X-DATERANGE while mapped to range in playlist".

    The current song's metadata still reaches clients via the existing
    PROGRAM-DATE-TIME + REST-poll path (every 10s) — the DATERANGE
    channel is purely an early-trigger signal that fires when the
    previous song's tag appears (i.e. when a song change has just
    happened in the source).
    """
    earliest_pdt = _earliest_segment_pdt_epoch(raw)
    cutoff = (earliest_pdt - 2) if earliest_pdt is not None else None

    # Sort by start so we know each song's successor (or lack thereof).
    songs_sorted = sorted(
        (s for s in songs if s.get("started_at", 0) > 0),
        key=lambda s: s["started_at"],
    )

    daterange_lines: list[str] = []
    seen: set[str] = set()
    for i, song in enumerate(songs_sorted):
        # Skip the latest — no successor yet, no committed end-date.
        if i + 1 == len(songs_sorted):
            continue

        successor_start = songs_sorted[i + 1]["started_at"]
        # Drop once the song's entire range is behind the playlist window.
        if cutoff is not None and successor_start <= cutoff:
            continue

        line = _daterange_for_song(song, end_at=successor_start)
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
