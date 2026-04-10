"""
HLS playlist generator — serves FFmpeg's AAC HLS playlist with windowing.

FFmpeg writes AAC .ts segments to /data/hls/segments/<epoch>.ts and a
raw playlist to /data/hls/live.m3u8. This generator reads FFmpeg's
playlist and serves a windowed version for live playback.

Endpoints (proxied by NGINX on port 8080):
  /index.m3u8                   → Live HLS playlist (AAC 64k, latest 65 segments)
  /index.m3u8?timestamp=<epoch> → Historical playlist starting at timestamp

DASH is served directly by NGINX from /data/dash/manifest.mpd.

Runs on 127.0.0.1:8081.
"""

import calendar
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

FFMPEG_M3U8 = "/data/hls/live.m3u8"
SEGMENTS_DIR = "/data/hls/segments"
LIVE_WINDOW_SIZE = 65
HISTORICAL_WINDOW_SIZE = 300

# (filename, duration, program_date_time)
SegmentInfo = tuple

_cache: list[SegmentInfo] = []
_cache_time = 0.0
_CACHE_TTL = 2


def parse_ffmpeg_m3u8() -> list[SegmentInfo]:
    """Parse FFmpeg's live.m3u8 for segment list with durations."""
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
            try:
                duration = float(line.split(":")[1].rstrip(","))
            except (ValueError, IndexError):
                duration = 6.0
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            pdt = line.split(":", 1)[1]
        elif line and not line.startswith("#"):
            segments.append((line, duration, pdt))
            pdt = None
            duration = 6.0

    return segments


def get_all_segments() -> list[SegmentInfo]:
    """Get segments combining FFmpeg's m3u8 (recent) + disk scan (older)."""
    global _cache, _cache_time

    now = time.time()
    if _cache and now - _cache_time < _CACHE_TTL:
        return _cache

    ffmpeg_segs = parse_ffmpeg_m3u8()
    ffmpeg_files = {s[0] for s in ffmpeg_segs}

    # Compute average duration and first timestamp for estimating old segments
    avg_dur = 6.0
    first_num = None
    first_epoch = None
    if ffmpeg_segs:
        durations = [s[1] for s in ffmpeg_segs]
        avg_dur = sum(durations) / len(durations)
        try:
            first_num = int(ffmpeg_segs[0][0].replace(".ts", ""))
        except ValueError:
            pass
        if ffmpeg_segs[0][2]:
            first_epoch = _parse_pdt(ffmpeg_segs[0][2])

    # Scan disk for all .ts files
    disk_nums = []
    try:
        for name in os.listdir(SEGMENTS_DIR):
            if name.endswith(".ts"):
                try:
                    disk_nums.append(int(name[:-3]))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    disk_nums.sort()

    result: list[SegmentInfo] = []
    for num in disk_nums:
        fname = f"{num}.ts"
        if fname in ffmpeg_files:
            for seg in ffmpeg_segs:
                if seg[0] == fname:
                    result.append(seg)
                    break
        else:
            # Estimate timestamp for old segments
            pdt = None
            if first_num is not None and first_epoch is not None:
                est_epoch = first_epoch + (num - first_num) * avg_dur
                pdt = _epoch_to_pdt(est_epoch)
            result.append((fname, avg_dur, pdt))

    _cache = result
    _cache_time = now
    return result


def _parse_pdt(pdt_str: str) -> float:
    clean = pdt_str.strip()
    if clean.endswith("Z"):
        clean = clean[:-1] + "+0000"
    if len(clean) > 5 and clean[-3] == ":":
        clean = clean[:-3] + clean[-2:]
    try:
        t = time.strptime(clean[:19], "%Y-%m-%dT%H:%M:%S")
        epoch = float(calendar.timegm(t))
        if "." in clean:
            ms = clean.split(".")[1][:3]
            epoch += int(ms) / 1000.0
        return epoch
    except (ValueError, IndexError):
        return time.time()


def _epoch_to_pdt(epoch: float) -> str:
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}+0000", t)


def _seg_epoch(seg: SegmentInfo) -> float:
    return _parse_pdt(seg[2]) if seg[2] else 0.0


def format_playlist(segs: list[SegmentInfo], is_live=True, is_event=False) -> str:
    if not segs:
        return "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:7\n#EXT-X-ENDLIST\n"

    try:
        first_seq = int(segs[0][0].replace(".ts", ""))
    except ValueError:
        first_seq = 0

    max_dur = max(s[1] for s in segs)
    td = int(max_dur) + 1

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{td}",
        f"#EXT-X-MEDIA-SEQUENCE:{first_seq}",
    ]
    if is_event:
        lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")

    for fname, dur, pdt in segs:
        if pdt:
            lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{pdt}")
        lines.append(f"#EXTINF:{dur:.6f},")
        lines.append(f"hls/segments/{fname}")

    if not is_live:
        lines.append("#EXT-X-ENDLIST")

    return "\n".join(lines) + "\n"


class PlaylistHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path not in ("/index.m3u8",):
            self.send_error(404)
            return

        segs = get_all_segments()
        if not segs:
            self.send_error(503, "No segments yet")
            return

        ts_param = params.get("timestamp", [None])[0]
        mode = params.get("mode", ["live"])[0]
        cacheable = False

        if ts_param:
            try:
                target = float(ts_param)
            except ValueError:
                self.send_error(400, "Invalid timestamp")
                return

            oldest = _seg_epoch(segs[0])
            newest = _seg_epoch(segs[-1])
            if target < oldest:
                target = oldest
            if target > newest + 10:
                playlist = format_playlist(segs[-LIVE_WINDOW_SIZE:])
            elif mode == "event":
                idx = next((i for i, s in enumerate(segs) if _seg_epoch(s) >= target), len(segs))
                playlist = format_playlist(segs[idx:idx + HISTORICAL_WINDOW_SIZE], is_live=False, is_event=True)
                cacheable = True
            else:
                idx = next((i for i, s in enumerate(segs) if _seg_epoch(s) >= target), len(segs))
                live_edge = max(0, len(segs) - LIVE_WINDOW_SIZE)
                if idx >= live_edge:
                    playlist = format_playlist(segs[-LIVE_WINDOW_SIZE:])
                else:
                    playlist = format_playlist(segs[idx:idx + LIVE_WINDOW_SIZE])
        else:
            window = segs[-LIVE_WINDOW_SIZE:] if len(segs) > LIVE_WINDOW_SIZE else segs
            playlist = format_playlist(window)

        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Cache-Control", "public, max-age=86400" if cacheable else "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(playlist.encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(os.environ.get("PLAYLIST_PORT", "8081"))
    server = HTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist generator on 127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
