"""
HLS playlist generator — stateless, CDN-cacheable, pure math.

Every playlist is deterministic: given a timestamp, the output is always
the same.  This means CDNs can cache both playlists and segments aggressively.

  Live:       /aac/index.m3u8              -> last ~6.5 min, cacheable 6s
  Master:     /master.m3u8                 -> static, cacheable forever

Runs on 127.0.0.1:8081.
"""

import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
LIVE_WINDOW_SIZE = 50  # 5 minutes (50 × 6s segments)

CODECS = {
    "aac": {
        "segments_dir": "/data/hls/aac/segments",
        "extension": ".ts",
        "prefix": "segments/",
    },
}


# ── Core math ──────────────────────────────────────────────────────────


def snap(epoch: float) -> int:
    """Snap an epoch to the nearest segment boundary (floor)."""
    e = int(epoch)
    return e - (e % SEGMENT_DURATION)


def _epoch_to_pdt(epoch: float) -> str:
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}Z", t)


def _latest_complete_seg() -> int:
    """Latest segment that is fully written (conservative)."""
    return snap(time.time()) - SEGMENT_DURATION


# ── Song metadata ──────────────────────────────────────────────────────


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


# ── Playlist builder ─────────────────────────────────────────────────


def _inject_songs(lines: list[str], seg_epoch: int, songs: list[dict], emitted: set[int]):
    """Inject EXT-X-DATERANGE for songs that start in this segment."""
    for si, song in enumerate(songs):
        if si in emitted:
            continue
        s_start = song.get("started_at", 0)
        if s_start >= seg_epoch and s_start < seg_epoch + SEGMENT_DURATION + 1:
            lines.append(_daterange_for_song(song, si))
            emitted.add(si)


def generate_playlist(
    codec: str,
    start_epoch: int,
    count: int,
) -> str:
    """Generate a live HLS playlist from pure arithmetic."""
    ext = CODECS[codec]["extension"]
    prefix = CODECS[codec]["prefix"]
    first_seq = start_epoch // SEGMENT_DURATION

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:9",
        f"#EXT-X-TARGETDURATION:{SEGMENT_DURATION + 1}",
        f"#EXT-X-MEDIA-SEQUENCE:{first_seq}",
        "#EXT-X-INDEPENDENT-SEGMENTS",
    ]

    songs = _get_songs()
    emitted: set[int] = set()

    for i in range(count):
        seg_epoch = start_epoch + i * SEGMENT_DURATION
        _inject_songs(lines, seg_epoch, songs, emitted)
        lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{_epoch_to_pdt(seg_epoch)}")
        lines.append(f"#EXTINF:{SEGMENT_DURATION}.000000,")
        lines.append(f"{prefix}{seg_epoch}{ext}")

    return "\n".join(lines) + "\n"


# ── Public playlist functions ─────────────────────────────────────────


# ── Disk helpers (status endpoint only) ──────────────────────────────


def _scan_disk(codec: str) -> list[int]:
    cfg = CODECS[codec]
    ext = cfg["extension"]
    nums = []
    try:
        for name in os.listdir(cfg["segments_dir"]):
            if name.endswith(ext):
                try:
                    nums.append(int(name.replace(ext, "")))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    nums.sort()
    return nums


# ── HTTP handler ──────────────────────────────────────────────────────


MASTER_PLAYLIST = """#EXTM3U
#EXT-X-VERSION:9
#EXT-X-INDEPENDENT-SEGMENTS

#EXT-X-STREAM-INF:BANDWIDTH=64000,CODECS="mp4a.40.5",AUDIO="audio"
aac/index.m3u8
"""


class PlaylistHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/master.m3u8":
            self._send_m3u8(MASTER_PLAYLIST, cache="public, max-age=86400")
            return
        if parsed.path == "/status.json":
            self._send_status()
            return

        codec = None
        if parsed.path in ("/aac/index.m3u8", "/index.m3u8"):
            codec = "aac"

        if codec is None:
            self.send_error(404)
            return

        # Generate live playlist — window ends near "now", starts ~6.5min in the past.
        now = snap(time.time())
        start = now - (LIVE_WINDOW_SIZE - 1) * SEGMENT_DURATION
        playlist = generate_playlist(codec, start, LIVE_WINDOW_SIZE)
        self._send_m3u8(playlist, cache="no-store")

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
            "latest_complete_segment": _latest_complete_seg(),
            "segment_duration": SEGMENT_DURATION,
        }

        for codec in CODECS:
            disk_nums = _scan_disk(codec)
            if disk_nums:
                result[codec] = {
                    "segments_on_disk": len(disk_nums),
                    "oldest_on_disk": disk_nums[0],
                    "newest_on_disk": disk_nums[-1],
                }
            else:
                result[codec] = {"segments_on_disk": 0}

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
    server = HTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist generator on 127.0.0.1:{port} (live, {SEGMENT_DURATION}s)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
