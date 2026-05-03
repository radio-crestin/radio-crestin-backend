"""
HLS playlist enhancer — reads FFmpeg's live.m3u8 and injects EXT-X-DATERANGE
song metadata tags. EXT-X-PROGRAM-DATE-TIME is emitted by FFmpeg
(`-hls_flags +program_date_time`) and passed through unchanged.

  Live:    /aac/index.m3u8 (= /index.m3u8)   -> ffmpeg playlist + DATERANGE tags
  Master:  /master.m3u8                      -> static, cacheable forever

DATERANGE tags are written into the playlist header (immediately after
EXT-X-MEDIA-SEQUENCE), not adjacent to a specific segment. Per RFC 8216
§4.4.5.1 they apply to the whole playlist; this avoids AVPlayer treating
them as segment boundaries (which causes seeks/fast-stops on iOS).

AVPlayer-friendly DATERANGE attributes (see prior advisory on AVPlayer
behavior with DATERANGE on live HLS):
  * No CLASS attribute (some classes trigger interstitial / ad behavior).
  * No DURATION attribute (DURATION is treated as a hard end and can
    cause playback to snap to wall-clock).
  * Stable per-song unique IDs (X-SONG-ID from backend, else epoch start)
    — never reused slot-style IDs like song-0, since AVPlayer reprocesses
    DATERANGEs whose ID reappears with different attributes.
  * START-DATE always emitted with millisecond precision.

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
HLS_LIST_SIZE = int(os.environ.get("HLS_LIST_SIZE", "65"))

FFMPEG_PLAYLIST = "/data/hls/aac/live.m3u8"


# ── Helpers ───────────────────────────────────────────────────────────


def _epoch_to_pdt(epoch: float) -> str:
    """Convert Unix epoch to ISO 8601 UTC timestamp with millisecond precision."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z", t)


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


def _daterange_for_song(song: dict) -> str | None:
    """Build an AVPlayer-friendly EXT-X-DATERANGE for a song.

    Returns None if the song lacks the minimum data (started_at + title/artist).
    """
    started_at = song.get("started_at", 0)
    if not started_at:
        return None

    # Always derive START-DATE from the epoch — `started_at_iso` from
    # metadata_monitor is second-precision and lacks the milliseconds
    # AVPlayer's metadata collector expects.
    start_iso = _epoch_to_pdt(started_at)

    title = song.get("title", song.get("raw", "")).replace('"', "'")
    artist = song.get("artist", "").replace('"', "'")
    if not title and not artist:
        return None

    thumbnail = song.get("thumbnail_url", "").replace('"', "'")
    song_id = song.get("song_id")
    station_id = song.get("station_id")

    # Stable, unique ID per song instance. Prefer the backend song_id
    # (immutable, globally unique); else use the epoch start (unique per
    # song occurrence on this station).
    if song_id:
        uid = f"song-{song_id}-{int(started_at)}"
    else:
        uid = f"song-{int(started_at)}"

    thumb_attr = f',X-THUMBNAIL-URL="{thumbnail}"' if thumbnail else ""
    song_id_attr = f',X-SONG-ID="{song_id}"' if song_id else ""
    station_id_attr = f',X-STATION-ID="{station_id}"' if station_id else ""

    return (
        f'#EXT-X-DATERANGE:ID="{uid}",'
        f'START-DATE="{start_iso}",'
        f'X-TITLE="{title}",'
        f'X-ARTIST="{artist}"'
        f'{thumb_attr}'
        f'{song_id_attr}'
        f'{station_id_attr}'
    )


# ── Playlist enhancer ─────────────────────────────────────────────────


def _window_start_epoch() -> float:
    """Songs older than this won't have their DATERANGE emitted.

    Bound to the live playlist window plus a small slack so songs that
    started just before the window still get one tag.
    """
    return time.time() - (HLS_LIST_SIZE * SEGMENT_DURATION + 60)


def enhance_playlist(raw_m3u8: str) -> str:
    """Pass through FFmpeg's playlist, injecting EXT-X-DATERANGE song
    metadata into the header block (after MEDIA-SEQUENCE / before the
    first segment).

    Per RFC 8216 §4.4.5.1, EXT-X-DATERANGE applies to the entire playlist;
    its position has no impact on which segment it 'belongs to'. Putting
    them in the header avoids AVPlayer treating each tag as a per-segment
    boundary marker.
    """
    songs = _get_songs()
    cutoff = _window_start_epoch()
    daterange_lines: list[str] = []
    seen_ids: set[str] = set()
    for song in songs:
        if song.get("started_at", 0) < cutoff:
            continue
        line = _daterange_for_song(song)
        if not line:
            continue
        # Dedupe in case `recent` contains the same song twice.
        m = re.match(r'#EXT-X-DATERANGE:ID="([^"]+)"', line)
        if m and m.group(1) in seen_ids:
            continue
        if m:
            seen_ids.add(m.group(1))
        daterange_lines.append(line)

    if not daterange_lines:
        return raw_m3u8

    out: list[str] = []
    inserted = False
    # Header tags (anything starting with `#` that is not a per-segment
    # marker — EXTINF / PROGRAM-DATE-TIME / DATERANGE — and not the `#EXTM3U`
    # opener). We insert DATERANGEs immediately before the first
    # segment-related line.
    SEGMENT_PREFIXES = ("#EXTINF", "#EXT-X-PROGRAM-DATE-TIME", "#EXT-X-BYTERANGE",
                        "#EXT-X-DISCONTINUITY", "#EXT-X-KEY", "#EXT-X-MAP")
    for line in raw_m3u8.rstrip("\n").split("\n"):
        if not inserted:
            stripped = line.lstrip()
            is_segment_line = (
                stripped.endswith(".ts") or stripped.startswith(SEGMENT_PREFIXES)
            )
            if is_segment_line:
                out.extend(daterange_lines)
                inserted = True
        out.append(line)

    # If the playlist had no segments yet (warmup), still emit the tags at
    # the end so clients that poll early see them.
    if not inserted:
        out.extend(daterange_lines)

    return "\n".join(out) + "\n"


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


# Single-rendition HE-AAC v1 stream (libfdk_aac aac_he @ 64k → mp4a.40.5).
MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-INDEPENDENT-SEGMENTS

#EXT-X-STREAM-INF:BANDWIDTH=64000,CODECS="mp4a.40.5",AUDIO="audio"
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

    # Some HLS players (and CDN health probes) issue HEAD before GET.
    # Without this, BaseHTTPRequestHandler returns 501, which nginx then
    # logs as an upstream error.
    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/master.m3u8", "/aac/index.m3u8", "/index.m3u8"):
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            except BrokenPipeError:
                pass
            return
        if parsed.path == "/status.json":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            except BrokenPipeError:
                pass
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
