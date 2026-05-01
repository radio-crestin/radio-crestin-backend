"""
HLS playlist enhancer — reads FFmpeg's live.m3u8 and adds EXT-X-PROGRAM-DATE-TIME
and EXT-X-DATERANGE (song metadata) tags.

FFmpeg writes segments with epoch-based filenames (e.g. 1776250253.ts) via -strftime 1.
This server reads the actual playlist, derives each segment's program date time from
its filename, and injects song metadata from /data/metadata/index.json.

  Live:       /aac/index.m3u8              -> enhanced FFmpeg playlist
  Master:     /master.m3u8                 -> static, cacheable forever

Runs on 127.0.0.1:8081.
"""

import json
import os
import re
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import posthog_reporter


class QuietHTTPServer(HTTPServer):
    """HTTPServer that silently ignores client-disconnect errors.

    nginx may close the upstream connection mid-response (proxy_read_timeout,
    client cancel). Default `socketserver.handle_error` prints a full
    traceback for each such event, which adds no signal in production logs.
    """

    def handle_error(self, request, client_address):
        exc_val = sys.exc_info()[1]
        if isinstance(exc_val, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)

SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))

# Path to FFmpeg's raw playlist
FFMPEG_PLAYLIST = "/data/hls/aac/live.m3u8"
# Directory holding the .ts segments and their <segment>.ts.pdt sidecars.
# Tests override this to point at a tmp dir.
SEGMENT_DIR = os.path.dirname(FFMPEG_PLAYLIST)


# ── Helpers ───────────────────────────────────────────────────────────


def _epoch_to_pdt(epoch: float) -> str:
    """Convert Unix epoch to ISO 8601 UTC timestamp for EXT-X-PROGRAM-DATE-TIME."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z", t)


def _extract_epoch(segment_line: str) -> int | None:
    """Extract the epoch timestamp from a segment filename like '1776250253.ts'."""
    m = re.search(r"(\d{10,})\.ts", segment_line)
    if m:
        return int(m.group(1))
    return None


# ── Stable per-segment PDT cache ──────────────────────────────────────
#
# A segment's program-date-time must NEVER change across playlist refreshes.
# The previous implementation re-anchored on the new first segment after each
# window slide and walked a cumulative-EXTINF offset from there; because the
# anchor is rounded to integer seconds (FFmpeg `-strftime %s.ts`) and EXTINF
# durations are float, the same segment file received a slightly different
# PDT (~10–14ms forward) on every slide. iOS AVPlayer interpreted the drift
# as a moving live-edge target and seeked forward to "catch up" — audible
# as the stream "jumping to different sections".
#
# Fix: compute each segment's PDT once, store it in a sidecar `<seg>.ts.pdt`
# file next to the segment, and reuse that value on every subsequent refresh.
# When FFmpeg's `delete_segments` removes a .ts, an orphan .pdt may linger
# briefly; cleanup.sh handles those.


def _pdt_sidecar(filename: str) -> str:
    return os.path.join(SEGMENT_DIR, filename + ".pdt")


def _load_cached_pdt(filename: str) -> float | None:
    try:
        with open(_pdt_sidecar(filename), "r") as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _save_cached_pdt_if_new(filename: str, pdt: float) -> None:
    """Write the sidecar atomically and only on first occurrence (O_EXCL).
    Once saved, a segment's PDT is immutable for the rest of its lifetime
    in the playlist. Failures (read-only fs, missing dir, race) silently
    no-op so the playlist still serves — we degrade to the legacy behavior
    in that case rather than 500ing.
    """
    path = _pdt_sidecar(filename)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except (FileExistsError, OSError):
        return
    try:
        os.write(fd, f"{pdt:.6f}".encode())
    except OSError:
        pass
    finally:
        os.close(fd)


def _compute_stable_pdts(segments: list[tuple[str, float]]) -> list[float | None]:
    """Compute a PDT for each segment in `segments` (list of (filename, extinf)).

    Algorithm:
      1. Load any cached PDTs from sidecars.
      2. If at least one segment has a cached PDT, use the earliest cached
         PDT as the anchor and fill missing PDTs by walking the EXTINF chain
         backward (for segments before it) and forward (for segments after).
      3. Otherwise (cold start: no cache yet for any segment in the window),
         seed PDT[0] from the first segment's filename epoch and fill forward.

    The walk preserves PDT[i+1] - PDT[i] == EXTINF[i] within a single playlist,
    and because it never recomputes a cached value, the per-segment PDT is
    stable across all subsequent refreshes.
    """
    pdts: list[float | None] = [_load_cached_pdt(fn) for fn, _ in segments]

    anchor_idx = next((i for i, p in enumerate(pdts) if p is not None), None)

    if anchor_idx is None and segments:
        first_epoch = _extract_epoch(segments[0][0])
        if first_epoch is not None:
            pdts[0] = float(first_epoch)
            anchor_idx = 0

    if anchor_idx is None:
        return pdts

    # Backward fill: PDT[i] = PDT[i+1] - EXTINF[i]  (segment i's own duration)
    for i in range(anchor_idx - 1, -1, -1):
        if pdts[i] is None:
            pdts[i] = pdts[i + 1] - segments[i][1]

    # Forward fill: PDT[i] = PDT[i-1] + EXTINF[i-1]  (previous segment's duration)
    for i in range(anchor_idx + 1, len(segments)):
        if pdts[i] is None:
            pdts[i] = pdts[i - 1] + segments[i - 1][1]

    return pdts


# ── Song metadata ─────────────────────────────────────────────────────


_song_cache: tuple[list[dict], float] | None = None
_SONG_CACHE_TTL = 3


def _get_songs() -> list[dict]:
    global _song_cache
    now = time.time()
    if _song_cache and now - _song_cache[1] < _SONG_CACHE_TTL:
        return _song_cache[0]
    try:
        with open("/data/metadata/index.json", "r") as f:
            data = json.load(f)
        songs = list(data.get("recent", []))
        cur = data.get("current")
        if cur and cur.get("raw"):
            songs.append(cur)
        songs.sort(key=lambda s: s.get("started_at", 0))
        _song_cache = (songs, now)
        return songs
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _daterange_for_song(song: dict, idx: int) -> str:
    start_iso = song.get("started_at_iso", "")
    if not start_iso:
        start_iso = _epoch_to_pdt(song.get("started_at", 0))
    start_iso = start_iso.replace("+0000", "Z")
    title = song.get("title", song.get("raw", "")).replace('"', "'")
    artist = song.get("artist", "").replace('"', "'")
    thumbnail = song.get("thumbnail_url", "").replace('"', "'")
    song_id = song.get("song_id")
    station_id = song.get("station_id")
    duration = song.get("duration_seconds")
    dur_attr = f',DURATION={duration}' if duration else ""
    thumb_attr = f',X-THUMBNAIL-URL="{thumbnail}"' if thumbnail else ""
    song_id_attr = f',X-SONG-ID="{song_id}"' if song_id else ""
    station_id_attr = f',X-STATION-ID="{station_id}"' if station_id else ""
    return (
        f'#EXT-X-DATERANGE:ID="song-{idx}",'
        f'START-DATE="{start_iso}",'
        f'CLASS="com.radiocrestin.song",'
        f'X-TITLE="{title}",'
        f'X-ARTIST="{artist}"'
        f'{thumb_attr}'
        f'{song_id_attr}'
        f'{station_id_attr}'
        f'{dur_attr}'
    )


# ── Playlist enhancer ─────────────────────────────────────────────────


def _parse_extinf(line: str) -> float | None:
    """Parse '#EXTINF:6.037189,' and return the float. Returns None if malformed."""
    try:
        val = line[len("#EXTINF:"):].rstrip(",").strip()
        return float(val)
    except (ValueError, IndexError):
        return None


def enhance_playlist(raw_m3u8: str) -> str:
    """Read FFmpeg's raw playlist and add EXT-X-PROGRAM-DATE-TIME + song DATERANGE tags.

    PDT is computed once per segment (via :func:`_compute_stable_pdts`) and
    cached in a sidecar so the same segment file always reports the same PDT,
    even after the playlist window slides. Within a single playlist the chain
    still satisfies PDT[i+1] - PDT[i] == EXTINF[i], which players depend on
    for smooth playback (and which earlier failed-fix attempts using raw
    filename epochs broke when ffmpeg restarted with overlapping wallclocks).

    Song DATERANGE matching continues to use the filename epoch (real
    wallclock) so song timestamps align with the actual broadcast.
    """
    songs = _get_songs()
    emitted_songs: set[int] = set()
    lines = raw_m3u8.rstrip("\n").split("\n")

    # First pass: collect (filename, extinf) pairs in playlist order.
    segments: list[tuple[str, float]] = []
    pending_extinf: float | None = None
    for line in lines:
        if line.startswith("#EXTINF:"):
            pending_extinf = _parse_extinf(line)
        elif line.endswith(".ts"):
            extinf = pending_extinf if pending_extinf is not None else float(SEGMENT_DURATION)
            segments.append((line.strip(), extinf))
            pending_extinf = None

    # Compute (and cache) a stable PDT for each segment.
    seg_pdts = _compute_stable_pdts(segments)
    for (fn, _), pdt in zip(segments, seg_pdts):
        if pdt is not None:
            _save_cached_pdt_if_new(fn, pdt)

    # Second pass: emit the enhanced playlist with PDT + DATERANGE tags.
    output: list[str] = []
    version_replaced = False
    seg_idx = 0
    for line in lines:
        if line.startswith("#EXT-X-VERSION:") and not version_replaced:
            output.append("#EXT-X-VERSION:9")
            version_replaced = True
            continue

        if line.endswith(".ts"):
            seg_epoch = _extract_epoch(line)

            # Song DATERANGE matching uses real wallclock (filename epoch).
            if seg_epoch is not None:
                for si, song in enumerate(songs):
                    if si in emitted_songs:
                        continue
                    s_start = song.get("started_at", 0)
                    if s_start >= seg_epoch and s_start < seg_epoch + SEGMENT_DURATION + 1:
                        output.append(_daterange_for_song(song, si))
                        emitted_songs.add(si)

            pdt = seg_pdts[seg_idx] if seg_idx < len(seg_pdts) else None
            if pdt is not None:
                output.append(f"#EXT-X-PROGRAM-DATE-TIME:{_epoch_to_pdt(pdt)}")
            output.append(line)
            seg_idx += 1
            continue

        output.append(line)

    return "\n".join(output) + "\n"


def _read_and_enhance() -> str | None:
    """Read FFmpeg's live.m3u8 and return the enhanced version."""
    try:
        with open(FFMPEG_PLAYLIST, "r") as f:
            raw = f.read()
        if not raw or "#EXTM3U" not in raw:
            return None
        return enhance_playlist(raw)
    except FileNotFoundError:
        return None


# ── HTTP handler ──────────────────────────────────────────────────────


MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:9
#EXT-X-INDEPENDENT-SEGMENTS

#EXT-X-STREAM-INF:BANDWIDTH=96000,CODECS="mp4a.40.2",AUDIO="audio"
aac/index.m3u8
"""


class PlaylistHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/master.m3u8":
            self._send_m3u8(MASTER_PLAYLIST, cache="public, max-age=86400")
            return
        if parsed.path == "/status.json":
            self._send_status()
            return

        if parsed.path in ("/aac/index.m3u8", "/index.m3u8"):
            playlist = _read_and_enhance()
            if playlist:
                self._send_m3u8(playlist, cache="no-store")
            else:
                self.send_error(503, "FFmpeg playlist not ready")
            return

        self.send_error(404)

    def _send_status(self):
        metadata = None
        try:
            with open("/data/metadata/index.json", "r") as f:
                metadata = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        pod_started_at = None
        try:
            with open("/data/pod_started_at", "r") as f:
                pod_started_at = float(f.read().strip())
        except (FileNotFoundError, ValueError):
            pass

        result = {
            "metadata": metadata,
            "pod_started_at": pod_started_at,
            "now": time.time(),
            "segment_duration": SEGMENT_DURATION,
        }

        body = json.dumps(result, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode())

    def _send_m3u8(self, body, cache="public, max-age=1"):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.apple.mpegurl")
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body.encode())
        except BrokenPipeError:
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(os.environ.get("PLAYLIST_PORT", "8081"))
    server = QuietHTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist enhancer on 127.0.0.1:{port} (reads {FFMPEG_PLAYLIST})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    posthog_reporter.install_global_handler("playlist_generator")
    main()
