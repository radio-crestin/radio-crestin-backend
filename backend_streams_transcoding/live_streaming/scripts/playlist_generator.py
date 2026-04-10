"""
Unified playlist generator for DASH + HLS from shared Opus fMP4 segments.

FFmpeg outputs a single DASH stream with 2 Opus qualities. This generator:
  - Serves the DASH manifest as-is
  - Generates HLS playlists (m3u8) pointing to the same fMP4 segments
  - HLS v7 supports fMP4 via EXT-X-MAP (no separate AAC encoding needed)

Segment layout on disk:
  /data/manifest.mpd                           - DASH manifest
  /data/segments/init-0.m4s                    - Init segment (low quality)
  /data/segments/init-1.m4s                    - Init segment (high quality)
  /data/segments/chunk-0-000000001.m4s         - Audio segment (low)
  /data/segments/chunk-1-000000001.m4s         - Audio segment (high)

HLS endpoints:
  /index.m3u8                       - Master playlist (two variants)
  /hls/low.m3u8                     - Low quality Opus variant
  /hls/high.m3u8                    - High quality Opus variant
  /index.m3u8?timestamp=<epoch>     - Historical playlist starting at timestamp
  /index.m3u8?quality=low           - Direct low quality

Runs on 127.0.0.1:8081.
"""

import calendar
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DASH_MANIFEST = "/data/manifest.mpd"
SEGMENTS_DIR = "/data/segments"
SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
LIVE_WINDOW_SIZE = 65
HISTORICAL_WINDOW_SIZE = 300

# Segment info from DASH manifest parsing
# (segment_number, duration_seconds, representation_id)
SegmentInfo = tuple


# ── DASH manifest parser ──────────────────────────────────────────

_manifest_cache = None
_manifest_cache_time = 0.0
_CACHE_TTL = 2


class DashManifest:
    """Parsed DASH manifest data."""

    def __init__(self):
        self.availability_start_time = 0.0
        self.representations = {}  # rep_id -> {bandwidth, init_seg, segments: [(number, duration, start_time)]}

    @staticmethod
    def parse(path: str) -> "DashManifest":
        """Parse a DASH MPD manifest."""
        result = DashManifest()
        try:
            tree = ET.parse(path)
        except (ET.ParseError, FileNotFoundError):
            return result

        root = tree.getroot()
        ns = ""
        # Handle namespace
        m = re.match(r"\{(.+)\}", root.tag)
        if m:
            ns = m.group(1)

        def tag(name):
            return f"{{{ns}}}{name}" if ns else name

        # Parse availabilityStartTime
        ast = root.get("availabilityStartTime", "")
        if ast:
            result.availability_start_time = _parse_iso_to_epoch(ast)

        # Parse adaptation sets and representations
        for period in root.iter(tag("Period")):
            for adapt_set in period.iter(tag("AdaptationSet")):
                for rep in adapt_set.iter(tag("Representation")):
                    rep_id = rep.get("id", "0")
                    bandwidth = int(rep.get("bandwidth", "0"))

                    # Find SegmentTemplate
                    seg_template = rep.find(tag("SegmentTemplate"))
                    if seg_template is None:
                        seg_template = adapt_set.find(tag("SegmentTemplate"))
                    if seg_template is None:
                        continue

                    init_seg = seg_template.get("initialization", "")
                    media_template = seg_template.get("media", "")
                    timescale = int(seg_template.get("timescale", "1"))
                    start_number = int(seg_template.get("startNumber", "1"))

                    # Replace $RepresentationID$
                    init_seg = init_seg.replace("$RepresentationID$", rep_id)

                    # Parse SegmentTimeline
                    segments = []
                    timeline = seg_template.find(tag("SegmentTimeline"))
                    if timeline is not None:
                        current_time = 0
                        seg_num = start_number
                        for s_elem in timeline.iter(tag("S")):
                            t = int(s_elem.get("t", str(current_time)))
                            d = int(s_elem.get("d", "0"))
                            r = int(s_elem.get("r", "0"))

                            current_time = t
                            for _ in range(r + 1):
                                start_epoch = result.availability_start_time + current_time / timescale
                                duration = d / timescale
                                segments.append((seg_num, duration, start_epoch))
                                current_time += d
                                seg_num += 1

                    result.representations[rep_id] = {
                        "bandwidth": bandwidth,
                        "init_seg": init_seg,
                        "media_template": media_template,
                        "segments": segments,
                    }

        return result


def get_manifest() -> DashManifest:
    """Get parsed DASH manifest with caching."""
    global _manifest_cache, _manifest_cache_time
    now = time.time()
    if _manifest_cache and now - _manifest_cache_time < _CACHE_TTL:
        return _manifest_cache
    _manifest_cache = DashManifest.parse(DASH_MANIFEST)
    _manifest_cache_time = now
    return _manifest_cache


def _parse_iso_to_epoch(iso_str: str) -> float:
    """Parse ISO 8601 datetime to epoch seconds."""
    clean = iso_str.strip().rstrip("Z")
    if "+" in clean[10:]:
        clean = clean[:clean.index("+", 10)]
    elif clean.count("-") > 2:
        # Has timezone offset like -0000
        pass
    try:
        if "." in clean:
            main, frac = clean.split(".")
            t = time.strptime(main, "%Y-%m-%dT%H:%M:%S")
            return float(calendar.timegm(t)) + float(f"0.{frac[:3]}")
        else:
            t = time.strptime(clean[:19], "%Y-%m-%dT%H:%M:%S")
            return float(calendar.timegm(t))
    except (ValueError, IndexError):
        return time.time()


def _epoch_to_pdt(epoch: float) -> str:
    """Convert epoch to HLS PROGRAM-DATE-TIME format."""
    t = time.gmtime(epoch)
    ms = int((epoch % 1) * 1000)
    return time.strftime(f"%Y-%m-%dT%H:%M:%S.{ms:03d}+0000", t)


def _segment_filename(media_template: str, rep_id: str, number: int) -> str:
    """Resolve DASH media template to actual filename."""
    name = media_template
    name = name.replace("$RepresentationID$", rep_id)
    # Handle $Number%09d$ pattern
    num_match = re.search(r"\$Number%(\d+)d\$", name)
    if num_match:
        width = int(num_match.group(1))
        name = re.sub(r"\$Number%\d+d\$", str(number).zfill(width), name)
    else:
        name = name.replace("$Number$", str(number))
    return name


# ── HLS playlist generation ───────────────────────────────────────

def build_hls_variant(manifest: DashManifest, rep_id: str, window_size: int = LIVE_WINDOW_SIZE,
                      is_live: bool = True, is_event: bool = False,
                      start_epoch: float = 0) -> str:
    """Build an HLS variant playlist for a specific representation."""
    rep = manifest.representations.get(rep_id)
    if not rep or not rep["segments"]:
        return "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:7\n#EXT-X-ENDLIST\n"

    segments = rep["segments"]

    # If seeking to a specific timestamp
    if start_epoch > 0:
        idx = 0
        for i, (num, dur, epoch) in enumerate(segments):
            if epoch >= start_epoch:
                idx = i
                break
        else:
            idx = len(segments)

        if is_event:
            segments = segments[idx:idx + HISTORICAL_WINDOW_SIZE]
        else:
            live_edge = max(0, len(segments) - window_size)
            if idx >= live_edge:
                segments = segments[-window_size:]
            else:
                segments = segments[idx:idx + window_size]
    else:
        # Live: latest window
        segments = segments[-window_size:] if len(segments) > window_size else segments

    if not segments:
        return "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:7\n#EXT-X-ENDLIST\n"

    max_dur = max(s[1] for s in segments)
    target_duration = int(max_dur) + 1
    first_seq = segments[0][0]

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        f"#EXT-X-MEDIA-SEQUENCE:{first_seq}",
        f'#EXT-X-MAP:URI="segments/{rep["init_seg"]}"',
    ]

    if is_event:
        lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")

    for num, dur, epoch in segments:
        filename = _segment_filename(rep["media_template"], rep_id, num)
        lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{_epoch_to_pdt(epoch)}")
        lines.append(f"#EXTINF:{dur:.6f},")
        lines.append(f"segments/{filename}")

    if not is_live:
        lines.append("#EXT-X-ENDLIST")

    return "\n".join(lines) + "\n"


def build_hls_master(manifest: DashManifest) -> str:
    """Build HLS master playlist with quality variants."""
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:7",
    ]

    # Sort representations by bandwidth (low first)
    sorted_reps = sorted(manifest.representations.items(), key=lambda x: x[1]["bandwidth"])

    quality_names = ["low", "high"]
    for i, (rep_id, rep_data) in enumerate(sorted_reps):
        name = quality_names[i] if i < len(quality_names) else f"q{i}"
        bw = rep_data["bandwidth"]
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bw},CODECS="opus",AUDIO="audio"')
        lines.append(f"hls/{name}.m3u8")

    return "\n".join(lines) + "\n"


# ── HTTP handler ───────────────────────────────────────────────────

class PlaylistHandler(BaseHTTPRequestHandler):
    """HTTP handler for HLS playlist generation from DASH segments."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        manifest = get_manifest()

        # Master playlist
        if path == "/index.m3u8" and "timestamp" not in params and "quality" not in params:
            playlist = build_hls_master(manifest)
            self._send_m3u8(playlist, cacheable=False)
            return

        # Quality variant or timestamped request
        if path in ("/index.m3u8", "/hls/low.m3u8", "/hls/high.m3u8"):
            # Determine quality
            quality = params.get("quality", ["high"])[0]
            if path == "/hls/low.m3u8":
                quality = "low"
            elif path == "/hls/high.m3u8":
                quality = "high"

            # Map quality name to representation ID
            sorted_reps = sorted(manifest.representations.items(), key=lambda x: x[1]["bandwidth"])
            if quality == "low" and sorted_reps:
                rep_id = sorted_reps[0][0]
            elif sorted_reps:
                rep_id = sorted_reps[-1][0]
            else:
                self.send_error(503, "No representations available")
                return

            timestamp_param = params.get("timestamp", [None])[0]
            mode = params.get("mode", ["live"])[0]
            cacheable = False
            start_epoch = 0

            if timestamp_param:
                try:
                    start_epoch = float(timestamp_param)
                    cacheable = True
                except ValueError:
                    self.send_error(400, "Invalid timestamp")
                    return

            playlist = build_hls_variant(
                manifest, rep_id,
                is_live=(mode != "event"),
                is_event=(mode == "event"),
                start_epoch=start_epoch,
            )
            self._send_m3u8(playlist, cacheable=cacheable)
            return

        self.send_error(404, "Not found")

    def _send_m3u8(self, text: str, cacheable: bool = False):
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        if cacheable:
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

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
