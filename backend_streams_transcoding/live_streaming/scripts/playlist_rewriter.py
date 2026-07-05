"""
HLS playlist rewriter — produces the two public playlists from ffmpeg's
live.m3u8, injecting EXT-X-DATERANGE song-metadata tags from
/data/metadata/index.json plus an EXT-X-START near-live join hint
(TIME-OFFSET = -2 x segment duration, for fast player startup) into both:

  index.m3u8  — the live playlist (same short window as ffmpeg's own list;
                what normal listeners poll every ~6s).
  dvr.m3u8    — the DVR variant: up to DVR_LIST_SIZE (1 hour) of segments
                accumulated from successive live.m3u8 reads. ffmpeg's
                delete threshold keeps that many segments on disk, so every
                URI in the DVR playlist is servable. Apps request this
                variant only when the user rewinds, so the ~10x larger
                playlist doesn't multiply steady-state playlist egress.
                Segment history (URI, EXTINF, PDT, sequence number) is
                persisted to dvr_history.json on the data volume so the
                window survives pod restarts; EXT-X-DISCONTINUITY is
                inserted where the segment-name boot prefix changes
                (i.e. across ffmpeg restarts).

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

SEGMENTS_DIR = Path("/data/hls/aac")
FFMPEG_PLAYLIST = SEGMENTS_DIR / "live.m3u8"
ENHANCED_PLAYLIST = SEGMENTS_DIR / "index.m3u8"
DVR_PLAYLIST = SEGMENTS_DIR / "dvr.m3u8"
# On the data volume next to the segments, so the DVR window survives pod
# restarts (cleanup.sh only sweeps *.ts / *.pdt, never this file).
DVR_HISTORY_PATH = SEGMENTS_DIR / "dvr_history.json"
METADATA_PATH = Path("/data/metadata/index.json")

POLL_INTERVAL = 1
SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
# Mirrors entrypoint.sh (1h DVR window / 6s segments); the pod exports the
# effective value, so this default only applies outside the pod.
DVR_LIST_SIZE = int(os.environ.get("DVR_LIST_SIZE", "600"))


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


def enhance(raw: str, songs: list[dict]) -> str:
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
    # Deterministic near-live join point: start 2 target durations behind
    # the live edge (the spec-minimum safe distance) instead of the player
    # default of 3 — shaves one segment of startup buffering. RFC 8216
    # §4.3.5.2: EXT-X-START is the *preferred* start point; explicit seeks
    # (the DVR use case) still win, so the DVR variant carries it too and
    # a DVR join before any seek also starts near live. No EXT-X-VERSION
    # requirement; unknown-tag-tolerant players ignore it.
    start_line: str | None = None
    if "#EXT-X-START:" not in raw:
        start_line = f"#EXT-X-START:TIME-OFFSET=-{2 * SEGMENT_DURATION}"

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
        iso = _epoch_to_pdt(current_started_at)
        metadata_changed_line = (
            f'#EXT-X-RC-METADATA-CHANGED:STARTED-AT="{iso}",'
            f'EPOCH={current_started_at}'
        )

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
        if not inserted:
            stripped = line.lstrip()
            if stripped.endswith(".ts") or stripped.startswith(SEGMENT_PREFIXES):
                out.extend(header_inserts)
                inserted = True
        out.append(line)

    if not inserted:
        out.extend(header_inserts)
    return "\n".join(out) + "\n"


def _parse_live_playlist(raw: str) -> tuple[str | None, list[dict]]:
    """Parse ffmpeg's live.m3u8 into (targetduration_line, segments).

    Each segment dict carries everything the DVR playlist needs to replay
    the entry verbatim later: name (URI), extinf line, optional PDT line,
    and its EXT-X-MEDIA-SEQUENCE number (header value + list position).
    """
    media_seq = 0
    target_line: str | None = None
    segments: list[dict] = []
    cur_extinf: str | None = None
    cur_pdt: str | None = None
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            try:
                media_seq = int(stripped.split(":", 1)[1])
            except (ValueError, IndexError):
                pass
        elif stripped.startswith("#EXT-X-TARGETDURATION:"):
            target_line = stripped
        elif stripped.startswith("#EXTINF:"):
            cur_extinf = stripped
        elif stripped.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            cur_pdt = stripped
        elif stripped.endswith(".ts") and not stripped.startswith("#"):
            segments.append({
                "name": stripped,
                "extinf": cur_extinf or f"#EXTINF:{SEGMENT_DURATION}.0,",
                "pdt": cur_pdt,
                "seq": media_seq + len(segments),
            })
            cur_extinf = None
            cur_pdt = None
    return target_line, segments


def _load_dvr_history() -> list[dict]:
    """Load persisted DVR history, dropping entries whose files are gone."""
    try:
        with open(DVR_HISTORY_PATH, "r") as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if not isinstance(entries, list):
        return []
    history = [
        e for e in entries
        if isinstance(e, dict)
        and all(k in e for k in ("name", "extinf", "seq"))
        and (SEGMENTS_DIR / e["name"]).exists()
    ]
    return history[-DVR_LIST_SIZE:]


def _update_dvr_history(history: list[dict], segments: list[dict]) -> bool:
    """Append newly seen segments; trim to the DVR window and to files that
    still exist on disk. Returns True when the history changed."""
    known = {e["name"] for e in history}
    changed = False
    for seg in segments:
        if seg["name"] not in known:
            history.append(seg)
            changed = True
    while len(history) > DVR_LIST_SIZE:
        history.pop(0)
        changed = True
    # ffmpeg's delete threshold outlives the DVR window, so this only fires
    # when retention was shortened or a manual sweep removed files.
    while history and not (SEGMENTS_DIR / history[0]["name"]).exists():
        history.pop(0)
        changed = True
    return changed


def _build_dvr_raw(history: list[dict], target_line: str | None,
                   independent_segments: bool) -> str:
    """Assemble the raw (pre-enhance) DVR playlist from the segment history.

    MEDIA-SEQUENCE is the first entry's recorded sequence number — it only
    moves forward as entries fall out of the window (epoch-seeded, so it
    also jumps forward, never back, across ffmpeg restarts). A restart is
    marked with EXT-X-DISCONTINUITY where the `<slug>-<boot>` segment-name
    prefix changes, matching the +initial_discontinuity mpegts flag on the
    segments themselves.
    """
    lines = ["#EXTM3U", "#EXT-X-VERSION:3"]
    if independent_segments:
        lines.append("#EXT-X-INDEPENDENT-SEGMENTS")
    lines.append(target_line or f"#EXT-X-TARGETDURATION:{SEGMENT_DURATION}")
    lines.append(f"#EXT-X-MEDIA-SEQUENCE:{history[0]['seq']}")
    prev_boot: str | None = None
    for entry in history:
        boot = entry["name"].rsplit("-", 1)[0]
        if prev_boot is not None and boot != prev_boot:
            lines.append("#EXT-X-DISCONTINUITY")
        prev_boot = boot
        if entry.get("pdt"):
            lines.append(entry["pdt"])
        lines.append(entry["extinf"])
        lines.append(entry["name"])
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, content: str) -> None:
    """Atomic write: tmp + os.replace. nginx never serves a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)


def main() -> None:
    print(
        f"playlist_rewriter: {FFMPEG_PLAYLIST} → {ENHANCED_PLAYLIST} + "
        f"{DVR_PLAYLIST} (DVR window: {DVR_LIST_SIZE} segments)",
        flush=True,
    )
    dvr_history = _load_dvr_history()
    if dvr_history:
        print(
            f"playlist_rewriter: restored {len(dvr_history)} DVR history "
            f"entries from {DVR_HISTORY_PATH}",
            flush=True,
        )
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

                    # DVR variant: accumulate segments across live.m3u8
                    # updates and emit the long-window playlist with the
                    # exact same enhance() pass (PDT comes with the stored
                    # entries; DATERANGE + RC-METADATA-CHANGED injection is
                    # identical to the live variant).
                    target_line, segments = _parse_live_playlist(raw)
                    history_changed = _update_dvr_history(dvr_history, segments)
                    if dvr_history:
                        dvr_raw = _build_dvr_raw(
                            dvr_history,
                            target_line,
                            "#EXT-X-INDEPENDENT-SEGMENTS" in raw,
                        )
                        write_atomic(DVR_PLAYLIST, enhance(dvr_raw, songs))
                    if history_changed:
                        write_atomic(
                            DVR_HISTORY_PATH, json.dumps(dvr_history),
                        )

                    last_playlist_mtime = playlist_stat.st_mtime
                    last_metadata_mtime = metadata_mtime
            except Exception as e:
                print(f"playlist_rewriter: error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
