"""
Dynamic HLS playlist generator with 7-day sliding window support.

Generates .m3u8 playlists on-the-fly based on available segments on disk.
Segments are named by epoch timestamp (e.g., 1718000000.ts) thanks to
FFmpeg's hls_start_number_source=epoch.

Endpoints (proxied by NGINX on port 8080):
  /index.m3u8                        → Live playlist (latest segments, no ENDLIST)
  /index.m3u8?timestamp=<epoch>      → Historical playlist starting at timestamp
  /index.m3u8?timestamp=<epoch>&mode=event → EVENT playlist for seeking (has ENDLIST)

Runs on 127.0.0.1:8081 (internal only, NGINX proxies to it).
"""

import glob
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SEGMENT_DURATION = int(os.environ.get("HLS_SEGMENT_DURATION", "6"))
HLS_DIR = "/data/hls/segments"
LIVE_WINDOW_SIZE = 65  # segments in a live playlist (~6.5 min)
HISTORICAL_WINDOW_SIZE = 300  # segments in a historical/event playlist (~30 min)

# Cache of available segments, refreshed periodically
_segments_cache = []
_segments_cache_time = 0
_CACHE_TTL = 2  # seconds


def get_available_segments():
    """Get sorted list of segment epoch timestamps from disk. Cached for 2s."""
    global _segments_cache, _segments_cache_time

    now = time.time()
    if now - _segments_cache_time < _CACHE_TTL and _segments_cache:
        return _segments_cache

    timestamps = []
    try:
        for name in os.listdir(HLS_DIR):
            if not name.endswith(".ts"):
                continue
            try:
                ts = int(name[:-3])  # strip .ts
                timestamps.append(ts)
            except ValueError:
                continue
    except FileNotFoundError:
        pass

    timestamps.sort()
    _segments_cache = timestamps
    _segments_cache_time = now
    return timestamps


def find_segment_index(segments, target_ts):
    """Binary search for the first segment >= target_ts."""
    lo, hi = 0, len(segments)
    while lo < hi:
        mid = (lo + hi) // 2
        if segments[mid] < target_ts:
            lo = mid + 1
        else:
            hi = mid
    return lo


def format_playlist(segment_timestamps, is_live=True, is_event=False):
    """Build an HLS playlist string from a list of segment timestamps."""
    if not segment_timestamps:
        return "#EXTM3U\n#EXT-X-VERSION:6\n#EXT-X-ENDLIST\n"

    # Media sequence = first segment's epoch / duration (monotonically increasing)
    seq = segment_timestamps[0] // SEGMENT_DURATION

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:6",
        f"#EXT-X-TARGETDURATION:{SEGMENT_DURATION}",
        f"#EXT-X-MEDIA-SEQUENCE:{seq}",
    ]

    if is_event:
        lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")

    for ts in segment_timestamps:
        # Add program date time for each segment (ISO 8601)
        lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{_epoch_to_iso(ts)}")
        lines.append(f"#EXTINF:{SEGMENT_DURATION}.0,")
        lines.append(f"hls/segments/{ts}.ts")

    if not is_live:
        lines.append("#EXT-X-ENDLIST")

    return "\n".join(lines) + "\n"


def _epoch_to_iso(epoch):
    """Convert epoch timestamp to ISO 8601 UTC string."""
    t = time.gmtime(epoch)
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", t)


def build_live_playlist(segments):
    """Build a live sliding window playlist from the latest segments."""
    window = segments[-LIVE_WINDOW_SIZE:] if len(segments) > LIVE_WINDOW_SIZE else segments
    return format_playlist(window, is_live=True, is_event=False)


def build_historical_playlist(segments, start_ts, mode="live"):
    """Build a playlist starting from a specific timestamp."""
    idx = find_segment_index(segments, start_ts)

    if mode == "event":
        # EVENT mode: return a larger window with ENDLIST for seeking
        window = segments[idx : idx + HISTORICAL_WINDOW_SIZE]
        return format_playlist(window, is_live=False, is_event=True)
    else:
        # Default: return a live-style window starting from timestamp
        # If timestamp is near the live edge, use live window instead
        live_edge_idx = max(0, len(segments) - LIVE_WINDOW_SIZE)
        if idx >= live_edge_idx:
            return build_live_playlist(segments)
        window = segments[idx : idx + LIVE_WINDOW_SIZE]
        return format_playlist(window, is_live=True, is_event=False)


class PlaylistHandler(BaseHTTPRequestHandler):
    """HTTP handler for dynamic HLS playlist generation."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Only handle playlist requests
        if parsed.path not in ("/index.m3u8", "/playlist.m3u8"):
            self.send_error(404, "Not found")
            return

        segments = get_available_segments()
        if not segments:
            self.send_error(503, "No segments available yet")
            return

        timestamp_param = params.get("timestamp", [None])[0]
        mode = params.get("mode", ["live"])[0]

        playlist = None
        is_cacheable = False

        if timestamp_param:
            try:
                target_ts = int(timestamp_param)
            except ValueError:
                self.send_error(400, "Invalid timestamp")
                return

            # Clamp to available range
            oldest = segments[0]
            newest = segments[-1]
            if target_ts < oldest:
                target_ts = oldest
            if target_ts > newest + SEGMENT_DURATION:
                # Future timestamp → serve live (not cacheable)
                playlist = build_live_playlist(segments)
            else:
                playlist = build_historical_playlist(segments, target_ts, mode)
                # Historical playlists are immutable — the segments won't change
                is_cacheable = True

        if playlist is None:
            playlist = build_live_playlist(segments)

        self._send_playlist(playlist, cacheable=is_cacheable)

    def _send_playlist(self, playlist_text, cacheable=False):
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        if cacheable:
            # Historical/event playlists are immutable — cache for 24h
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            # Live playlists must never be cached
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.end_headers()
        self.wfile.write(playlist_text.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress request logging to reduce noise."""
        pass


def main():
    port = int(os.environ.get("PLAYLIST_PORT", "8081"))
    server = HTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist generator listening on 127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
