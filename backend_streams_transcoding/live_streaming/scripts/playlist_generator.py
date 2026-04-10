"""
Dynamic HLS playlist generator with 7-day sliding window support.

Parses FFmpeg's live.m3u8 to get correct segment durations and timestamps,
then generates playlists dynamically for live and historical playback.

FFmpeg uses hls_start_number_source=epoch which sets the STARTING segment
number to the epoch second, then increments by 1 per segment. Each segment
is ~6 seconds. The filename does NOT equal the epoch timestamp of the segment.

This generator reads FFmpeg's m3u8 to get the authoritative segment list
with correct EXTINF durations and PROGRAM-DATE-TIME tags.

Endpoints (proxied by NGINX on port 8080):
  /index.m3u8                        -> Live playlist (latest segments, no ENDLIST)
  /index.m3u8?timestamp=<epoch>      -> Historical playlist starting at timestamp
  /index.m3u8?timestamp=<epoch>&mode=event -> EVENT playlist for seeking (has ENDLIST)

Runs on 127.0.0.1:8081 (internal only, NGINX proxies to it).
"""

import calendar
import os
import re
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

FFMPEG_M3U8 = "/data/hls/live.m3u8"
SEGMENTS_DIR = "/data/hls/segments"
LIVE_WINDOW_SIZE = 65   # segments in a live playlist (~6.5 min at 6s each)
HISTORICAL_WINDOW_SIZE = 300  # segments in historical playlist (~30 min)

# Segment info: (filename, duration, program_date_time)
SegmentInfo = tuple  # (str, float, str|None)


# ── FFmpeg m3u8 parser ─────────────────────────────────────────────

_segments_cache: list[SegmentInfo] = []
_segments_cache_time: float = 0
_CACHE_TTL = 2  # seconds


def parse_ffmpeg_m3u8() -> list[SegmentInfo]:
    """Parse FFmpeg's live.m3u8 to get the authoritative segment list.

    Returns list of (filename, duration, program_date_time) tuples.
    """
    try:
        with open(FFMPEG_M3U8, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    segments = []
    duration = 6.0
    pdt = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            # #EXTINF:6.013967,
            try:
                duration = float(line.split(":")[1].rstrip(","))
            except (ValueError, IndexError):
                duration = 6.0
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            pdt = line.split(":", 1)[1]
        elif line and not line.startswith("#"):
            # This is a segment filename (e.g., "1775816500.ts")
            segments.append((line, duration, pdt))
            pdt = None
            duration = 6.0

    return segments


def get_all_segments() -> list[SegmentInfo]:
    """Get all available segments by combining FFmpeg's m3u8 with disk scan.

    FFmpeg's m3u8 has the most recent segments with correct durations.
    Older segments (beyond m3u8 window) use estimated duration from disk.
    """
    global _segments_cache, _segments_cache_time

    now = time.time()
    if now - _segments_cache_time < _CACHE_TTL and _segments_cache:
        return _segments_cache

    # Parse FFmpeg's m3u8 for authoritative recent segments
    ffmpeg_segments = parse_ffmpeg_m3u8()
    ffmpeg_filenames = {s[0] for s in ffmpeg_segments}

    # Get the media sequence and first PDT from FFmpeg's playlist
    # to compute timestamps for older segments
    first_ffmpeg_number = None
    first_ffmpeg_pdt_epoch = None
    default_duration = 6.0

    if ffmpeg_segments:
        # Extract segment number from first segment filename
        try:
            first_ffmpeg_number = int(ffmpeg_segments[0][0].replace(".ts", ""))
        except ValueError:
            pass
        # Parse first PDT
        if ffmpeg_segments[0][2]:
            first_ffmpeg_pdt_epoch = _parse_pdt_to_epoch(ffmpeg_segments[0][2])
        # Use average duration from FFmpeg segments
        durations = [s[1] for s in ffmpeg_segments]
        if durations:
            default_duration = sum(durations) / len(durations)

    # Scan disk for all segment files (including those older than FFmpeg's window)
    disk_numbers = []
    try:
        for name in os.listdir(SEGMENTS_DIR):
            if name.endswith(".ts"):
                try:
                    disk_numbers.append(int(name[:-3]))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass

    disk_numbers.sort()

    # Build the full segment list
    all_segments: list[SegmentInfo] = []

    for num in disk_numbers:
        filename = f"{num}.ts"
        if filename in ffmpeg_filenames:
            # Use FFmpeg's authoritative data
            for seg in ffmpeg_segments:
                if seg[0] == filename:
                    all_segments.append(seg)
                    break
        else:
            # Older segment: estimate timestamp from its position relative to FFmpeg's first
            pdt = None
            if first_ffmpeg_number is not None and first_ffmpeg_pdt_epoch is not None:
                offset_segments = num - first_ffmpeg_number
                estimated_epoch = first_ffmpeg_pdt_epoch + (offset_segments * default_duration)
                pdt = _epoch_to_pdt(estimated_epoch)
            all_segments.append((filename, default_duration, pdt))

    _segments_cache = all_segments
    _segments_cache_time = now
    return all_segments


def _parse_pdt_to_epoch(pdt_str: str) -> float:
    """Parse a PROGRAM-DATE-TIME string to epoch seconds."""
    # Format: 2026-04-10T10:09:11.791+0000 or 2026-04-10T10:09:11.000Z
    clean = pdt_str.strip()
    # Remove timezone suffix for parsing
    if clean.endswith("Z"):
        clean = clean[:-1] + "+0000"
    # Remove colon in timezone offset if present (e.g., +00:00 -> +0000)
    if len(clean) > 5 and clean[-3] == ":":
        clean = clean[:-3] + clean[-2:]

    try:
        t = time.strptime(clean[:19], "%Y-%m-%dT%H:%M:%S")
        epoch = float(calendar.timegm(t))  # UTC, no local timezone
        # Add milliseconds
        if "." in clean:
            ms_str = clean.split(".")[1][:3]
            epoch += int(ms_str) / 1000.0
        return epoch
    except (ValueError, IndexError):
        return time.time()


def _epoch_to_pdt(epoch: float) -> str:
    """Convert epoch to PROGRAM-DATE-TIME format."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}+0000", t)


def _get_segment_epoch(seg: SegmentInfo) -> float:
    """Get the epoch timestamp for a segment."""
    if seg[2]:
        return _parse_pdt_to_epoch(seg[2])
    return 0.0


# ── Playlist formatting ───────────────────────────────────────────

def format_playlist(
    segments: list[SegmentInfo],
    is_live: bool = True,
    is_event: bool = False,
) -> str:
    """Build an HLS playlist from segment info tuples."""
    if not segments:
        return "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-ENDLIST\n"

    # Media sequence = first segment number (from filename)
    try:
        first_num = int(segments[0][0].replace(".ts", ""))
    except ValueError:
        first_num = 0

    # Compute max segment duration for TARGETDURATION (must be >= any EXTINF)
    max_dur = max(seg[1] for seg in segments)
    target_duration = int(max_dur) + 1  # Round up per HLS spec

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        f"#EXT-X-MEDIA-SEQUENCE:{first_num}",
    ]

    if is_event:
        lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")

    for filename, duration, pdt in segments:
        if pdt:
            lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{pdt}")
        lines.append(f"#EXTINF:{duration:.6f},")
        lines.append(f"hls/segments/{filename}")

    if not is_live:
        lines.append("#EXT-X-ENDLIST")

    return "\n".join(lines) + "\n"


def build_live_playlist(segments: list[SegmentInfo]) -> str:
    """Build a live sliding window playlist from the latest segments."""
    window = segments[-LIVE_WINDOW_SIZE:] if len(segments) > LIVE_WINDOW_SIZE else segments
    return format_playlist(window, is_live=True, is_event=False)


def build_historical_playlist(
    segments: list[SegmentInfo], target_epoch: float, mode: str = "live"
) -> str:
    """Build a playlist starting from a specific timestamp."""
    # Find the segment closest to the requested timestamp
    idx = 0
    for i, seg in enumerate(segments):
        seg_epoch = _get_segment_epoch(seg)
        if seg_epoch >= target_epoch:
            idx = i
            break
    else:
        idx = len(segments)

    if mode == "event":
        window = segments[idx: idx + HISTORICAL_WINDOW_SIZE]
        return format_playlist(window, is_live=False, is_event=True)
    else:
        # If near live edge, return live playlist
        live_edge_idx = max(0, len(segments) - LIVE_WINDOW_SIZE)
        if idx >= live_edge_idx:
            return build_live_playlist(segments)
        window = segments[idx: idx + LIVE_WINDOW_SIZE]
        return format_playlist(window, is_live=True, is_event=False)


# ── HTTP handler ───────────────────────────────────────────────────

class PlaylistHandler(BaseHTTPRequestHandler):
    """HTTP handler for dynamic HLS playlist generation."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path not in ("/index.m3u8", "/playlist.m3u8"):
            self.send_error(404, "Not found")
            return

        segments = get_all_segments()
        if not segments:
            self.send_error(503, "No segments available yet")
            return

        timestamp_param = params.get("timestamp", [None])[0]
        mode = params.get("mode", ["live"])[0]

        playlist = None
        is_cacheable = False

        if timestamp_param:
            try:
                target_ts = float(timestamp_param)
            except ValueError:
                self.send_error(400, "Invalid timestamp")
                return

            oldest_epoch = _get_segment_epoch(segments[0])
            newest_epoch = _get_segment_epoch(segments[-1])

            if target_ts < oldest_epoch:
                target_ts = oldest_epoch
            if target_ts > newest_epoch + 10:
                playlist = build_live_playlist(segments)
            else:
                playlist = build_historical_playlist(segments, target_ts, mode)
                is_cacheable = True

        if playlist is None:
            playlist = build_live_playlist(segments)

        self._send_playlist(playlist, cacheable=is_cacheable)

    def _send_playlist(self, playlist_text: str, cacheable: bool = False):
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        if cacheable:
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(playlist_text.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    port = int(os.environ.get("PLAYLIST_PORT", "8081"))
    server = HTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist generator listening on 127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
