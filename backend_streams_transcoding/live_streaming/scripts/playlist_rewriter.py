"""
HLS playlist rewriter: renders the public playlists from ffmpeg's
live.m3u8, re-stamped with wall-clock EXT-X-PROGRAM-DATE-TIME, and injects
song metadata from /data/metadata/index.json (EXT-X-DATERANGE,
EXT-X-RC-METADATA-CHANGED) plus an EXT-X-START near-live join hint:

  index.m3u8     the live playlist: the newest LIVE_LIST_SIZE published
                 segments (what normal listeners poll every ~6 s).
  index-2m.m3u8  index.m3u8 byte for byte except EXT-X-START, which is
  index-5m.m3u8  2 / 5 minutes behind live (clamped to the window, see
                 _offset_variant). Apps that play that far behind live
                 load one instead of index.m3u8 plus a seek, so the player
                 starts there without first downloading segments at the
                 near-live start. Same segments and URIs as index.m3u8, so
                 segment caching and egress are shared.
  dvr.m3u8       the DVR variant: up to DVR_LIST_SIZE published segments
                 (1 hour). Apps request it only when the user rewinds, so
                 the ~6x larger playlist doesn't multiply steady-state
                 egress.

index.m3u8 and dvr.m3u8 are windows over one persisted segment history
(dvr_history.json), not copies of live.m3u8:

  * Every segment gets a wall-clock PDT once, when it first appears
    (wallclock_pdt), and keeps it in every later version of either
    playlist, across rewriter restarts too. ffmpeg's own PDT is ignored.
  * An ffmpeg restart appends to both playlists after
    EXT-X-DISCONTINUITY instead of replacing them: EXT-X-MEDIA-SEQUENCE
    and EXT-X-DISCONTINUITY-SEQUENCE are stored per segment, so any window
    satisfies RFC 8216 6.2.2. Segments wallclock_pdt withholds (replayed
    audio, drift resync) are skipped the same way, after
    EXT-X-DISCONTINUITY.
  * ffmpeg deletes nothing. The history drops its oldest segments once
    they are older than the DVR window plus 5 minutes (by file mtime or
    PDT, whichever is earlier), or up to the newest one whose file is gone;
    cleanup.sh deletes a file 5 minutes later by mtime, so a listed URI
    never 404s.
  * EXT-X-TARGETDURATION is the largest rounded EXTINF ever published (at
    least SEGMENT_DURATION) and never decreases.

Contract for clients (C-1, C-2):

  * PDT is wall clock (UTC), one tag per segment, never changed once
    published, and never going backwards. It advances by at least the
    previous EXTINF and jumps forward wherever audio was lost: after an
    upstream stall inside one ffmpeg run, and after a discontinuity. Such
    jumps are routine inside a single window, so a player position must be
    mapped to the segment containing it and that segment's PDT; integrating
    a playhead across segments in the PDT domain (first PDT + position)
    drifts behind by every jump crossed.
  * Every playlist is rewritten only when its bytes change, so the
    Last-Modified nginx serves is when the content last changed (a new
    segment or new metadata), not a metadata heartbeat.

Why separate files instead of rewriting live.m3u8 in place:
  - ffmpeg writes live.m3u8 via temp-file + atomic rename (`+temp_file`); we
    don't fight that. We read the whole file (always intact thanks to the
    rename), produce our playlists, and atomic-rename our own output.
  - nginx serves the playlists *statically*: no proxy_pass to Python, no
    per-request cost, no Python becoming a single point of failure for
    playlist availability. If the rewriter falls behind, nginx just keeps
    serving the last good playlists.

EXT-X-DATERANGE was added in HLS v6 (RFC 8216 §4.4.5.1), so when we inject
any DATERANGE entry we also bump #EXT-X-VERSION:3 → #EXT-X-VERSION:6.

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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import posthog_reporter
import wallclock_pdt

SEGMENTS_DIR = Path("/data/hls/aac")
FFMPEG_PLAYLIST = SEGMENTS_DIR / "live.m3u8"
ENHANCED_PLAYLIST = SEGMENTS_DIR / "index.m3u8"
DVR_PLAYLIST = SEGMENTS_DIR / "dvr.m3u8"
# index.m3u8 with EXT-X-START INDEX_2M_OFFSET / INDEX_5M_OFFSET behind live.
INDEX_2M_PLAYLIST = SEGMENTS_DIR / "index-2m.m3u8"
INDEX_5M_PLAYLIST = SEGMENTS_DIR / "index-5m.m3u8"
# On the data volume next to the segments, so the stamps survive rewriter
# restarts (and pod restarts with USE_PVC); cleanup.sh only sweeps *.ts.
DVR_HISTORY_PATH = SEGMENTS_DIR / "dvr_history.json"
METADATA_PATH = Path("/data/metadata/index.json")
# Written by scraper_engine after Django accepted a song-change report dated
# by the ICY start: the song as Django stored it (title, artist, ids,
# proxied thumbnail) for the X-* hints of EXT-X-RC-METADATA-CHANGED.
NOW_PLAYING_PATH = Path("/data/metadata/now_playing.json")
# Size caps for the EXT-X-RC-METADATA-CHANGED hint attributes.
HINT_TEXT_LIMIT = 256
HINT_URL_LIMIT = 1024

POLL_INTERVAL = 1
# Re-render at least this often, so expired segments also leave the
# playlists while ffmpeg and the metadata are idle (an upstream outage).
REFRESH_INTERVAL = 60
SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
# Mirrors entrypoint.sh (1h DVR window / 6s segments); the pod exports the
# effective value, so this default only applies outside the pod.
DVR_LIST_SIZE = int(os.environ.get("DVR_LIST_SIZE", "600"))
# Published entries in index.m3u8; mirrors entrypoint.sh (660 s / 6 s).
LIVE_LIST_SIZE = int(os.environ.get("HLS_LIST_SIZE", "110"))
# Entries older than this leave both playlists; cleanup.sh deletes their
# files 5 minutes later (DVR window + 10 min), so a listed URI never 404s.
DVR_MAX_AGE = int(os.environ.get("DVR_WINDOW_SECONDS", "3600")) + 300
# EXT-X-START distance from the live edge, in target durations.
START_OFFSET_SEGMENTS = 3
# EXT-X-START distance of index-2m.m3u8 / index-5m.m3u8, in seconds: the
# offsets the app plays behind live by default and on a car, unstable or
# slow connection (its seek_mode_manager).
INDEX_2M_OFFSET = 120
INDEX_5M_OFFSET = 300
# Those variants start at least this long after the oldest segment they
# list (mirrors the app's _dvrTrailingSafetyMargin): the window slides by a
# segment every few seconds, so a start near its head would leave the
# playlist before the player got going.
VARIANT_TRAILING_MARGIN = 75


# Tags that belong to the segment after them (RFC 8216 4.3.2). The header
# block ends at the first of these. EXT-X-DISCONTINUITY is matched exactly
# in _starts_segment(): as a prefix it would also match the header tag
# EXT-X-DISCONTINUITY-SEQUENCE.
SEGMENT_PREFIXES = (
    "#EXTINF",
    "#EXT-X-PROGRAM-DATE-TIME",
    "#EXT-X-BYTERANGE",
    "#EXT-X-KEY",
    "#EXT-X-MAP",
)


def _starts_segment(line: str) -> bool:
    """True for the first line of a media segment's tags or its URI."""
    stripped = line.strip()
    return (stripped.endswith(".ts") or stripped == "#EXT-X-DISCONTINUITY"
            or stripped.startswith(SEGMENT_PREFIXES))


def _epoch_to_pdt(epoch: float) -> str:
    """ISO-8601 UTC with millisecond precision — matches the format
    AVPlayer's metadata collector expects on START-DATE."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z", t)


def _load_songs() -> list[dict] | None:
    """Songs from index.json, [] when there is none yet, or None when the
    file could not be parsed (retry on the next poll instead of publishing
    a playlist without metadata tags)."""
    try:
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return None
    songs = list(data.get("recent", []))
    cur = data.get("current")
    if cur and cur.get("raw"):
        songs.append(cur)
    songs.sort(key=lambda s: s.get("started_at", 0))
    return songs


def _load_now_playing() -> dict | None:
    """scraper_engine's last accepted report, or None."""
    try:
        with open(NOW_PLAYING_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _quoted(value: object, limit: int) -> str | None:
    """`value` as an RFC 8216 quoted-string body: no double quote, CR or LF
    (or any other control character), whitespace collapsed, at most
    `limit` characters. None when nothing is left."""
    if value is None:
        return None
    text = "".join(" " if unicodedata.category(c) == "Cc" else c
                   for c in str(value)).replace('"', "'")
    text = " ".join(text.split())[:limit].rstrip()
    return text or None


def _positive_id(value: object) -> int | None:
    """A Django primary key from JSON, or None (bool is not an id)."""
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _hint_url(value: object) -> str | None:
    """An http(s) URL that fits a quoted string unchanged, or None."""
    if (isinstance(value, str) and value.startswith(("https://", "http://"))
            and len(value) <= HINT_URL_LIMIT
            and _quoted(value, HINT_URL_LIMIT) == value):
        return value
    return None


def _hint_attributes(current: dict, now_playing: dict | None) -> list[str]:
    """X-* attributes describing the current song, only when Django's
    accepted report is about this exact song instance (same ICY title and
    same start), so they equal what the API returns for that song.

    The thumbnail is the proxied URL the API serves (`song_thumbnail_url`),
    never the raw source URL: a client showing the hint keeps the same
    image when the API data replaces it. A field an older Django does not
    return is simply left out.
    """
    if not now_playing or now_playing.get("raw") != current.get("raw"):
        return []
    if abs(float(now_playing.get("started_at") or 0)
           - float(current.get("started_at") or 0)) > 0.001:
        return []
    attrs = []
    for name, key in (("X-TITLE", "title"), ("X-ARTIST", "artist")):
        value = _quoted(now_playing.get(key), HINT_TEXT_LIMIT)
        if value:
            attrs.append(f'{name}="{value}"')
    for name, key in (("X-SONG-ID", "song_id"),
                      ("X-ARTIST-ID", "song_artist_id")):
        value = _positive_id(now_playing.get(key))
        if value is not None:
            attrs.append(f'{name}="{value}"')
    url = _hint_url(now_playing.get("song_thumbnail_url"))
    if url is not None:
        attrs.append(f'X-THUMBNAIL-URL="{url}"')
    return attrs


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
    # An attribute with an empty quoted string (X-ARTIST="") makes AVPlayer
    # reject the whole playlist (-12642 "Empty or blank attribute value"):
    # new loads fail and a playing item stops refreshing and runs dry. So
    # every text value goes through _quoted and an empty one is left out.
    title = (_quoted(song.get("title"), HINT_TEXT_LIMIT)
             or _quoted(song.get("raw"), HINT_TEXT_LIMIT))
    artist = _quoted(song.get("artist"), HINT_TEXT_LIMIT)
    if not title and not artist:
        return None
    thumbnail = _quoted(song.get("thumbnail_url"), HINT_URL_LIMIT)
    song_id = song.get("song_id")
    station_id = song.get("station_id")

    # Stable, unique ID per song instance: its start in milliseconds (plus
    # the backend song_id when known). Reusing slot-style IDs would cause
    # AVPlayer to reprocess the range when attributes change. Whole seconds
    # are not unique: a reconnect burst delivers several titles within
    # milliseconds, and two songs sharing an ID meant the second one's
    # attributes replaced the first one's under that ID (RFC 8216
    # 4.4.5.1.1) once the first left the window.
    start_ms = int(round(started_at * 1000))
    uid = f"song-{song_id}-{start_ms}" if song_id else f"song-{start_ms}"

    parts = [
        f'ID="{uid}"',
        f'START-DATE="{_epoch_to_pdt(started_at)}"',
        f'END-DATE="{_epoch_to_pdt(end_at)}"',
    ]
    if title:
        parts.append(f'X-TITLE="{title}"')
    if artist:
        parts.append(f'X-ARTIST="{artist}"')
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


def _current_song_started_at(songs: list[dict]) -> int | None:
    """Return the started_at epoch (Unix seconds, UTC) of the *current*
    song — the largest-started_at entry in the buffer — or None when
    there is no known current song.

    Powers the EXT-X-RC-METADATA-CHANGED real-time signal. The current
    song is the one for which DATERANGE is intentionally suppressed
    (RFC 8216 §4.4.5.1.1 immutability concern), so without this signal
    the only way mobile learns about a current-song change is the next
    polling tick. The marker plugs that gap without re-introducing the
    DATERANGE attribute-mutation hazard.
    """
    valid = [s for s in songs if s.get("started_at", 0) > 0]
    if not valid:
        return None
    return int(max(s["started_at"] for s in valid))


def enhance(raw: str, songs: list[dict],
            now_playing: dict | None = None) -> str:
    """Return the playlist with DATERANGE tags injected into the header
    block (between EXT-X-MEDIA-SEQUENCE and the first segment), an
    EXT-X-RC-METADATA-CHANGED marker carrying the current song's
    started_at epoch, and the version bumped to 6 if any DATERANGE was
    added.

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

    EXT-X-RC-METADATA-CHANGED rules (custom tag, mobile-only signal):

    * Carries the current song's `started_at` as a Unix-epoch UTC
      timestamp. When this value flips between playlist fetches, mobile
      clients know a song change has happened in the source. Because
      the signal is the source-timeline timestamp (not wall-clock now),
      mobile can ALIGN the metadata refresh to the playback timeline
      — important when the user is seeking behind live edge by 2-4 min.

    * Per RFC 8216 §4.1, unrecognised tags are ignored. Older app
      versions, AVPlayer, ExoPlayer, hls.js — all silently skip this
      tag. Safe to deploy without coordinated client release.

    * The "RC-" prefix avoids collision with future standard tags. The
      tag is emitted UNCONDITIONALLY when there is a current song —
      it does not depend on the DATERANGE emission path, so it works
      even when only one song is known (the case where DATERANGE
      cannot emit anything).
    """
    # Deterministic near-live join point: 3 target durations behind the
    # live edge, the closest RFC 8216 §4.3.5.2 allows ("SHOULD NOT be
    # within three target durations"). media3 adopts it as its target live
    # offset. EXT-X-START is the *preferred* start point; explicit seeks
    # (the DVR use case) still win, so the DVR variant carries it too and
    # a DVR join before any seek also starts near live. No EXT-X-VERSION
    # requirement; unknown-tag-tolerant players ignore it.
    start_line: str | None = None
    if "#EXT-X-START:" not in raw:
        offset = START_OFFSET_SEGMENTS * _target_duration_of(raw)
        start_line = f"#EXT-X-START:TIME-OFFSET=-{offset}"

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

    current_started_at = _current_song_started_at(songs)
    metadata_changed_line: str | None = None
    if current_started_at is not None:
        # STARTED-AT is the source-timeline timestamp. EPOCH duplicates the
        # same value in seconds so naive parsers don't have to ISO-decode
        # to compare. Both attributes describe the same instant.
        # EPOCH stays the first `EPOCH=` of the line: app versions in the
        # field read it with RegExp(r'EPOCH=(\d+)').firstMatch. The
        # optional X-* song hints come after it.
        iso = _epoch_to_pdt(current_started_at)
        current = max((s for s in songs if s.get("started_at", 0) > 0),
                      key=lambda s: s["started_at"])
        metadata_changed_line = ",".join([
            f'#EXT-X-RC-METADATA-CHANGED:STARTED-AT="{iso}"',
            f'EPOCH={current_started_at}',
            *_hint_attributes(current, now_playing),
        ])

    header_inserts: list[str] = []
    if start_line is not None:
        header_inserts.append(start_line)
    header_inserts.extend(daterange_lines)
    if metadata_changed_line is not None:
        header_inserts.append(metadata_changed_line)

    if not header_inserts:
        return raw

    out: list[str] = []
    inserted = False
    for line in raw.rstrip("\n").split("\n"):
        if line.startswith("#EXT-X-VERSION:"):
            # DATERANGE requires v6; the custom RC tag has no version
            # requirement (unknown tags are ignored at any version).
            # Only bump when DATERANGE is actually being emitted.
            out.append("#EXT-X-VERSION:6" if daterange_lines else line)
            continue
        if not inserted and _starts_segment(line):
            out.extend(header_inserts)
            inserted = True
        out.append(line)

    if not inserted:
        out.extend(header_inserts)
    return "\n".join(out) + "\n"


def _target_duration_of(raw: str) -> int:
    """EXT-X-TARGETDURATION of a playlist (SEGMENT_DURATION if absent)."""
    match = re.search(r"^#EXT-X-TARGETDURATION:(\d+)", raw, re.MULTILINE)
    return int(match.group(1)) if match else SEGMENT_DURATION


def _extinf_seconds(extinf: str) -> float:
    """Duration of an `#EXTINF:<seconds>,` line."""
    try:
        return float(extinf.split(":", 1)[1].split(",", 1)[0])
    except (IndexError, ValueError):
        return float(SEGMENT_DURATION)


def _rounded_extinf(extinf: str) -> int:
    """EXTINF rounded to the nearest integer, as RFC 8216 4.3.3.1 compares
    it with EXT-X-TARGETDURATION."""
    return int(_extinf_seconds(extinf) + 0.5)


def _offset_variant(index: str, offset: int) -> str:
    """index.m3u8's text with its EXT-X-START line replaced by one `offset`
    seconds behind live.

    The offset is clamped, in whole seconds rounded down, to leave
    VARIANT_TRAILING_MARGIN of the window before the start. Should that be
    less than index.m3u8's own START_OFFSET_SEGMENTS target durations (a
    window of about 1.5 minutes, after a pod start or a long outage), the
    variant is index.m3u8 unchanged: players start where index.m3u8 starts.
    """
    window = sum(_extinf_seconds(line) for line in index.split("\n")
                 if line.startswith("#EXTINF:"))
    offset = min(offset, int(window) - VARIANT_TRAILING_MARGIN)
    if offset < START_OFFSET_SEGMENTS * _target_duration_of(index):
        return index
    variant, replaced = re.subn(r"^#EXT-X-START:.*$",
                                f"#EXT-X-START:TIME-OFFSET=-{offset}",
                                index, count=1, flags=re.MULTILINE)
    if not replaced:
        # Every index.m3u8 _publish renders has one (enhance() adds it).
        # Serving the text unchanged would start apps near live while they
        # rely on the variant to start behind live.
        raise ValueError("index.m3u8 has no EXT-X-START line")
    return variant


def _parse_live_playlist(raw: str) -> tuple[dict, list[dict]]:
    """Parse ffmpeg's live.m3u8 into (header, segments).

    ffmpeg's own EXT-X-PROGRAM-DATE-TIME lines are ignored on purpose: they
    are muxer-init time plus media duration, not wall clock (see
    wallclock_pdt). So is its EXT-X-TARGETDURATION: it only covers ffmpeg's
    own window. Each segment dict carries its URI, EXTINF line and
    duration, and its EXT-X-MEDIA-SEQUENCE number.
    """
    header = {"independent": "#EXT-X-INDEPENDENT-SEGMENTS" in raw}
    media_seq = 0
    segments: list[dict] = []
    cur_extinf: str | None = None
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            try:
                media_seq = int(stripped.split(":", 1)[1])
            except (ValueError, IndexError):
                pass
        elif stripped.startswith("#EXTINF:"):
            cur_extinf = stripped
        elif stripped.endswith(".ts") and not stripped.startswith("#"):
            extinf = cur_extinf or f"#EXTINF:{SEGMENT_DURATION}.0,"
            segments.append({
                "name": stripped,
                "extinf": extinf,
                "duration": _extinf_seconds(extinf),
                "seq": media_seq + len(segments),
            })
            cur_extinf = None
    return header, segments


def _pdt_line(epoch: float) -> str:
    """`#EXT-X-PROGRAM-DATE-TIME` in the exact text shape ffmpeg writes
    (`YYYY-MM-DDTHH:MM:SS.mmm+0000`), so every parser of today's playlists
    reads the re-stamped ones unchanged."""
    millis = int(round(epoch * 1000))
    whole, ms = divmod(millis, 1000)
    return time.strftime(
        f"#EXT-X-PROGRAM-DATE-TIME:%Y-%m-%dT%H:%M:%S.{ms:03d}+0000",
        time.gmtime(whole),
    )


def _observe(seg: dict) -> wallclock_pdt.Observation:
    return wallclock_pdt.Observation(seg["name"], seg["duration"],
                                     _segment_mtime(seg["name"]))


def _segment_mtime(name: str) -> float | None:
    try:
        return (SEGMENTS_DIR / name).stat().st_mtime
    except OSError:
        return None


# ── Segment history (persisted) ──
#
# One entry per segment ffmpeg ever listed, oldest first:
#   name, extinf, seq (ffmpeg's media sequence), wall (stamped PDT epoch),
#   mtime, paced, residual, kind (wallclock_pdt.KIND_*), ahead (drifting
#   ahead after replayed audio), published, and for published entries:
#   pub_seq  contiguous media sequence of published entries (both playlists),
#   disc     discontinuity sequence number: +1 at each new ffmpeg boot and
#            after withheld entries.
# Both playlists are windows over the published entries: index.m3u8 (and
# its offset variants) the newest LIVE_LIST_SIZE, dvr.m3u8 the newest
# DVR_LIST_SIZE. A segment's PDT, media sequence and discontinuity number
# are fixed when it is first published, so every playlist that lists it
# agrees (RFC 8216 6.2.1/6.2.2), including across ffmpeg restarts and
# rewriter restarts.
# Next to the entries:
#   high_water       per boot still in live.m3u8 or history, the newest
#                    ffmpeg sequence number ever stamped (survives trimming)
#   target_duration  EXT-X-TARGETDURATION of both playlists

HISTORY_VERSION = 3


def _new_history() -> dict:
    return {"version": HISTORY_VERSION, "entries": [], "high_water": {},
            "target_duration": SEGMENT_DURATION}


def _load_history() -> dict:
    """Load the persisted history, dropping entries whose files are gone.

    A history written by an older rewriter (different or missing version)
    is discarded instead of migrated: its entries carry ffmpeg's PDT, and
    re-dating an already-published segment would change its PDT under
    connected players. Its segments simply stop being listed; players see
    the same playlist reset as on any restart.
    """
    try:
        with open(DVR_HISTORY_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _new_history()
    if not isinstance(data, dict) or data.get("version") != HISTORY_VERSION:
        print("playlist_rewriter: discarding history of an older format",
              flush=True)
        return _new_history()
    history = _new_history()
    history["entries"] = [
        e for e in data.get("entries", [])
        if isinstance(e, dict) and "name" in e and "wall" in e
    ]
    marks = data.get("high_water")
    if isinstance(marks, dict):
        history["high_water"] = {boot: seq for boot, seq in marks.items()
                                 if isinstance(seq, int)}
    target = data.get("target_duration")
    if isinstance(target, int):
        history["target_duration"] = max(target, SEGMENT_DURATION)
    _trim_history(history, time.time())
    return history


def _stamp_of(entry: dict) -> wallclock_pdt.Stamp:
    return wallclock_pdt.Stamp(
        name=entry["name"], duration=_extinf_seconds(entry["extinf"]),
        mtime=entry.get("mtime"), wall=entry["wall"],
        paced=bool(entry.get("paced")), residual=entry.get("residual"),
        kind=entry.get("kind", wallclock_pdt.KIND_CHAIN),
        ahead=bool(entry.get("ahead")),
    )


def _published_end(entries: list[dict]) -> wallclock_pdt.BootEnd | None:
    """Where the newest published entry ends."""
    for e in reversed(entries):
        if e.get("published"):
            return wallclock_pdt.boot_end(_stamp_of(e))
    return None


def _published(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("published")]


def _append_stamp(entries: list[dict], seg: dict,
                  stamp: wallclock_pdt.Stamp) -> None:
    entry = {
        "name": seg["name"], "extinf": seg["extinf"], "seq": seg["seq"],
        "wall": stamp.wall, "mtime": stamp.mtime, "paced": stamp.paced,
        "residual": stamp.residual, "kind": stamp.kind,
        "ahead": stamp.ahead, "published": stamp.published,
    }
    if stamp.published:
        prev = next((e for e in reversed(entries) if e.get("published")),
                    None)
        if prev is None:
            # Seeded like EXT-X-MEDIA-SEQUENCE (ffmpeg numbers segments
            # from the epoch), so a replacement pod's playlist never goes
            # back to a discontinuity number the previous pod used.
            entry["pub_seq"] = entry["disc"] = seg["seq"]
        else:
            new_boot = (wallclock_pdt.boot_of(prev["name"])
                        != wallclock_pdt.boot_of(seg["name"]))
            skipped = entries[-1] is not prev
            entry["pub_seq"] = prev["pub_seq"] + 1
            entry["disc"] = prev["disc"] + (1 if new_boot or skipped else 0)
    last = entries[-1] if entries else None
    entries.append(entry)
    # One report per run of same-kind stamps (a boot's back-chained burst,
    # a restart's withheld duplicates), not one per segment.
    continues_run = (
        last is not None and last.get("kind") == stamp.kind
        and wallclock_pdt.boot_of(last["name"])
        == wallclock_pdt.boot_of(seg["name"]))
    if stamp.kind != wallclock_pdt.KIND_CHAIN and not continues_run:
        jump = (None if last is None else
                stamp.wall - (last["wall"] + _extinf_seconds(last["extinf"])))
        _report_stamp(stamp, jump)


def _report_stamp(stamp: wallclock_pdt.Stamp, jump: float | None) -> None:
    """Boot anchors, re-anchors, replays and withheld segments are rare and
    worth a log line plus a PostHog event; chain stamps are not.

    `residual_s` is anchor minus stamp: for a `replay` it is minus the drift
    ahead of the wall clock (at most wallclock_pdt.MAX_DRIFT; in a new boot
    or after withheld segments: the drift carried over). `jump_s` is how far
    the stamp lies after the end of the previous segment in history: the
    audio lost in a stall for a `reanchor`, the gap between runs for a
    `boot`, minus the withheld replay for a `duplicate`, minus the drift
    that triggered a `resync`.
    """
    residual = (None if stamp.residual is None
                else round(stamp.residual, 3))
    jump = None if jump is None else round(jump, 3)
    print(
        f"playlist_rewriter: pdt {stamp.kind} {stamp.name} "
        f"wall={stamp.wall:.3f} residual={residual} jump={jump}",
        flush=True,
    )
    posthog_reporter.capture_event("pdt_stamp", {
        "kind": stamp.kind, "segment": stamp.name, "residual_s": residual,
        "jump_s": jump,
    })


def _stamp_new_segments(history: dict, segments: list[dict],
                        now: float) -> bool:
    """Stamp, in order, the segments of live.m3u8 that history lacks.

    The segments of a boot that has no anchor yet stay pending (absent from
    history and therefore from both playlists) until
    wallclock_pdt.anchor_new_boot() can stamp them. Returns True when
    history changed.
    """
    entries = history["entries"]
    changed = _update_high_water(history, segments)
    # Only segments after the newest one ever stamped for their boot: an
    # older one missing from history was trimmed, never re-stamp it (also
    # not once its whole boot has left history, e.g. ffmpeg's last
    # live.m3u8 during an outage longer than the DVR window).
    fresh = [s for s in segments if _pending(s, history["high_water"])]
    i = 0
    while i < len(fresh):
        seg = fresh[i]
        boot = wallclock_pdt.boot_of(seg["name"])
        last = entries[-1] if entries else None
        if last is not None and wallclock_pdt.boot_of(last["name"]) == boot:
            observation = _observe(seg)
            if (last.get("published") and wallclock_pdt.is_burst(
                    observation, last.get("mtime"))):
                held = [s for s in fresh[i:]
                        if wallclock_pdt.boot_of(s["name"]) == boot]
                stamps = wallclock_pdt.stamp_burst(
                    _stamp_of(last), [_observe(s) for s in held], now)
                if not stamps:
                    break
                for seg_, stamp in zip(held, stamps):
                    _append_stamp(entries, seg_, stamp)
                changed = True
                i += len(stamps)
                continue
            stamp = wallclock_pdt.stamp_next(
                _stamp_of(last), observation, floor=_published_end(entries))
            _append_stamp(entries, seg, stamp)
            changed = True
            i += 1
            continue
        pending = [s for s in fresh[i:]
                   if wallclock_pdt.boot_of(s["name"]) == boot]
        stamps = wallclock_pdt.anchor_new_boot(
            [_observe(s) for s in pending], now, _published_end(entries))
        if not stamps:
            break
        for seg_, stamp in zip(pending, stamps):
            _append_stamp(entries, seg_, stamp)
        changed = True
        i += len(pending)
    return _update_high_water(history, segments) or changed


def _pending(seg: dict, high_water: dict[str, int]) -> bool:
    """True for a segment newer than every one stamped for its boot."""
    return seg["seq"] > high_water.get(wallclock_pdt.boot_of(seg["name"]), -1)


def _update_high_water(history: dict, segments: list[dict]) -> bool:
    """Raise each boot's high-water mark to its newest history entry and
    forget boots that left both live.m3u8 and history (ffmpeg never lists
    them again). Returns True when the marks changed."""
    marks = dict(history["high_water"])
    for e in history["entries"]:
        boot = wallclock_pdt.boot_of(e["name"])
        marks[boot] = max(marks.get(boot, e["seq"]), e["seq"])
    current = {wallclock_pdt.boot_of(x["name"])
               for x in segments + history["entries"]}
    marks = {boot: seq for boot, seq in marks.items() if boot in current}
    if marks == history["high_water"]:
        return False
    history["high_water"] = marks
    return True


def _oldest_time(entry: dict) -> float:
    """The earlier of the entry's PDT and its file's mtime: cleanup.sh
    deletes by mtime, and PDT may run ahead of it."""
    mtime = entry.get("mtime")
    return entry["wall"] if mtime is None else min(entry["wall"], mtime)


def _trim_history(history: dict, now: float) -> bool:
    """Drop the oldest entries: those older than DVR_MAX_AGE, up to the
    newest one whose file is gone, and beyond the newest DVR_LIST_SIZE
    published ones. Returns True when history changed.

    Only a head is ever dropped and nothing is renumbered: pub_seq and disc
    travel with each entry, so trimming only advances EXT-X-MEDIA-SEQUENCE
    and EXT-X-DISCONTINUITY-SEQUENCE (RFC 8216 6.2.1).
    """
    entries = history["entries"]
    oldest = now - DVR_MAX_AGE
    start = 0
    for i, e in enumerate(entries):
        if (_oldest_time(e) < oldest
                or not (SEGMENTS_DIR / e["name"]).exists()):
            start = i + 1
    kept = entries[start:]
    published = _published(kept)
    if len(published) > DVR_LIST_SIZE:
        first = published[-DVR_LIST_SIZE]
        kept = kept[next(i for i, e in enumerate(kept) if e is first):]
    if len(kept) == len(entries):
        return False
    history["entries"] = kept
    return True


def _raise_target_duration(history: dict) -> bool:
    """Raise target_duration to the largest rounded EXTINF published
    (RFC 8216 4.3.3.1); it never decreases. Returns True when raised."""
    target = max([history["target_duration"]]
                 + [_rounded_extinf(e["extinf"])
                    for e in _published(history["entries"])])
    if target == history["target_duration"]:
        return False
    history["target_duration"] = target
    return True


def _render_media_playlist(entries: list[dict], header: dict,
                           target_duration: int) -> str:
    """Render a media playlist (pre-enhance) from published entries."""
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    if header.get("independent"):
        lines.append("#EXT-X-INDEPENDENT-SEGMENTS")
    lines.append(f"#EXT-X-TARGETDURATION:{target_duration}")
    lines.append(f"#EXT-X-MEDIA-SEQUENCE:{entries[0]['pub_seq']}")
    lines.append(f"#EXT-X-DISCONTINUITY-SEQUENCE:{entries[0]['disc']}")
    prev_disc = entries[0]["disc"]
    for entry in entries:
        if entry["disc"] != prev_disc:
            lines.append("#EXT-X-DISCONTINUITY")
        prev_disc = entry["disc"]
        lines.append(entry["extinf"])
        lines.append(_pdt_line(entry["wall"]))
        lines.append(entry["name"])
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, content: str) -> None:
    """Atomic write: tmp + os.replace. nginx never serves a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def write_if_changed(path: Path, content: str) -> bool:
    """write_atomic() unless `path` already holds exactly `content`.

    Keeps the file's mtime, which nginx serves as Last-Modified, equal to
    when the content last changed. Clients compare Last-Modified with the
    live edge's PDT; a rewrite with identical bytes (index.json heartbeat)
    would only add noise. Returns True when the file was written.
    """
    try:
        if path.read_text() == content:
            return False
    except (FileNotFoundError, UnicodeDecodeError):
        pass
    write_atomic(path, content)
    return True


def _publish_offset_variants(index: str, now: float) -> None:
    """Write index-2m.m3u8 and index-5m.m3u8 from index.m3u8's text.

    Runs after index.m3u8 and dvr.m3u8 are written, and a failure is only
    reported, so it never holds those back. A variant that failed is
    removed: nginx then answers 404 and apps fall back to index.m3u8 plus a
    seek, where a stale copy would stop advancing under its listeners.
    """
    for path, offset in ((INDEX_2M_PLAYLIST, INDEX_2M_OFFSET),
                         (INDEX_5M_PLAYLIST, INDEX_5M_OFFSET)):
        try:
            write_if_changed(path, _offset_variant(index, offset))
        except Exception as error:
            _report_error(error, now)
            path.unlink(missing_ok=True)


def _publish(history: dict, raw: str, songs: list[dict], now: float,
             now_playing: dict | None = None) -> bool:
    """Stamp new segments and render every playlist from the history.

    Returns True when every segment of `raw` was stamped (it may have been
    trimmed since), i.e. nothing is waiting for a boot anchor and the next
    poll may skip an unchanged live.m3u8.

    New stamps are persisted before any playlist lists them, and `history`
    only takes them once they are on disk: a rewriter killed (or a write
    failing) in between never leaves a published stamp that a restarted
    rewriter would date differently (RFC 8216 6.2.1).
    """
    header, segments = _parse_live_playlist(raw)
    draft = {**history, "entries": list(history["entries"])}
    changed = _stamp_new_segments(draft, segments, now)
    changed = _trim_history(draft, now) or changed
    changed = _raise_target_duration(draft) or changed
    if changed:
        write_atomic(DVR_HISTORY_PATH, json.dumps(draft))
        history.update(draft)
    published = _published(history["entries"])
    target = history["target_duration"]
    if published:
        live = published[-LIVE_LIST_SIZE:]
        index = enhance(_render_media_playlist(live, header, target), songs,
                        now_playing)
        write_if_changed(ENHANCED_PLAYLIST, index)
        write_if_changed(DVR_PLAYLIST, enhance(
            _render_media_playlist(published, header, target), songs,
            now_playing))
        _publish_offset_variants(index, now)
    else:
        # Everything expired (a long outage): serve no playlist rather than
        # one whose segments cleanup.sh deletes.
        ENHANCED_PLAYLIST.unlink(missing_ok=True)
        DVR_PLAYLIST.unlink(missing_ok=True)
        INDEX_2M_PLAYLIST.unlink(missing_ok=True)
        INDEX_5M_PLAYLIST.unlink(missing_ok=True)
    return not any(_pending(s, history["high_water"]) for s in segments)


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


# A failure that repeats every poll is reported once per this period.
ERROR_REPORT_INTERVAL = 600
_last_error_report: tuple[str, float] = ("", 0.0)


def _report_error(error: Exception, now: float) -> None:
    """Log every failure; send each distinct one to PostHog at most once
    per ERROR_REPORT_INTERVAL (the loop retries every POLL_INTERVAL)."""
    global _last_error_report
    print(f"playlist_rewriter: error: {error}", flush=True)
    key = f"{type(error).__name__}: {error}"
    last_key, last_at = _last_error_report
    if key == last_key and now - last_at < ERROR_REPORT_INTERVAL:
        return
    _last_error_report = (key, now)
    posthog_reporter.capture_exception(
        error, context={"component": "playlist_rewriter"})


def main() -> None:
    print(
        f"playlist_rewriter: {FFMPEG_PLAYLIST} → {ENHANCED_PLAYLIST} + "
        f"{DVR_PLAYLIST} (DVR window: {DVR_LIST_SIZE} segments)",
        flush=True,
    )
    history = _load_history()
    if history["entries"]:
        print(
            f"playlist_rewriter: restored {len(history['entries'])} history "
            f"entries from {DVR_HISTORY_PATH}",
            flush=True,
        )
    last_playlist_mtime = 0.0
    last_metadata_key = (0.0, 0.0)
    last_publish = 0.0
    while True:
        try:
            playlist_mtime = FFMPEG_PLAYLIST.stat().st_mtime
            metadata_key = (_mtime(METADATA_PATH), _mtime(NOW_PLAYING_PATH))
            if (playlist_mtime != last_playlist_mtime
                    or metadata_key != last_metadata_key
                    or time.time() - last_publish >= REFRESH_INTERVAL):
                with open(FFMPEG_PLAYLIST, "r") as f:
                    raw = f.read()
                songs = _load_songs()
                if raw and "#EXTM3U" in raw and songs is not None:
                    last_publish = time.time()
                    if _publish(history, raw, songs, last_publish,
                                _load_now_playing()):
                        last_playlist_mtime = playlist_mtime
                    last_metadata_key = metadata_key
        except FileNotFoundError:
            pass
        except Exception as e:
            _report_error(e, time.time())
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    posthog_reporter.install_global_handler("playlist_rewriter")
    main()
