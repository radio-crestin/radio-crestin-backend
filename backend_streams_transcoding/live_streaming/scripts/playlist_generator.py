"""
HLS playlist generator with LL-HLS Delivery Directives (RFC 8216bis).

Supports:
  - Blocking reload: _HLS_msn=N holds until segment N is ready
  - Segment skipping: _HLS_skip=YES replaces old segments with EXT-X-SKIP
  - Historical playback: timestamp=<epoch> starts from any point
  - Gap detection: EXT-X-DISCONTINUITY for missing segments
  - S3-backed 7-day history via segment index
  - Rich metadata: EXT-X-DATERANGE with title, artist, thumbnail URL

Endpoints (proxied by NGINX on port 8080):
  /master.m3u8                              -> Master playlist
  /aac/index.m3u8                           -> AAC+ live playlist
  /aac/index.m3u8?timestamp=<epoch>         -> Historical playback
  /aac/index.m3u8?_HLS_msn=N               -> Blocking reload (wait for segment N)
  /aac/index.m3u8?_HLS_msn=N&_HLS_skip=YES -> Blocking + skip old segments
  /status.json                              -> Status with gaps
  /availability.json                        -> Full availability map

Runs on 127.0.0.1:8081 (threaded for blocking reload).
"""

import calendar
import json
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
LIVE_WINDOW_SIZE = 65
BLOCK_TIMEOUT = int(os.environ.get("HLS_BLOCK_TIMEOUT", "12"))
SKIP_UNTIL = SEGMENT_DURATION * 6

CODECS = {
    "aac": {
        "ffmpeg_m3u8": "/data/hls/aac/live.m3u8",
        "segments_dir": "/data/hls/aac/segments",
        "extension": ".ts",
        "prefix": "segments/",
        "init_segment": None,
    },
}

S3_INDEX_PATH = "/data/s3_index.json"

SegmentInfo = tuple

_cache: dict[str, tuple[list[SegmentInfo], float]] = {}
_CACHE_TTL = 1
_s3_index_cache: dict | None = None
_s3_index_mtime = 0.0


def parse_ffmpeg_m3u8(codec: str) -> list[SegmentInfo]:
    cfg = CODECS[codec]
    try:
        with open(cfg["ffmpeg_m3u8"], "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    segments = []
    duration = float(SEGMENT_DURATION)
    pdt = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            try:
                duration = float(line.split(":")[1].rstrip(","))
            except (ValueError, IndexError):
                duration = float(SEGMENT_DURATION)
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            pdt = line.split(":", 1)[1]
        elif line and not line.startswith("#"):
            fname = line.rsplit("/", 1)[-1] if "/" in line else line
            segments.append((fname, duration, pdt))
            pdt = None
            duration = float(SEGMENT_DURATION)

    return segments


def _build_segments(codec: str, ffmpeg_segs, disk_nums, extra_nums=None):
    cfg = CODECS[codec]
    ext = cfg["extension"]
    ffmpeg_files = {s[0] for s in ffmpeg_segs}

    avg_dur = float(SEGMENT_DURATION)
    first_num = None
    first_epoch = None
    if ffmpeg_segs:
        durations = [s[1] for s in ffmpeg_segs]
        avg_dur = sum(durations) / len(durations)
        try:
            first_num = int(ffmpeg_segs[0][0].replace(ext, ""))
        except ValueError:
            pass
        if ffmpeg_segs[0][2]:
            first_epoch = _parse_pdt(ffmpeg_segs[0][2])

    all_nums = sorted(disk_nums | (extra_nums or set()))

    result: list[SegmentInfo] = []
    for num in all_nums:
        fname = f"{num}{ext}"
        if fname in ffmpeg_files:
            for seg in ffmpeg_segs:
                if seg[0] == fname:
                    result.append(seg)
                    break
        else:
            pdt = None
            if first_num is not None and first_epoch is not None:
                est_epoch = first_epoch + (num - first_num) * avg_dur
                pdt = _epoch_to_pdt(est_epoch)
            elif num > 0:
                pdt = _epoch_to_pdt(float(num))
            result.append((fname, avg_dur, pdt))

    return result


def _scan_disk(codec: str) -> set[int]:
    cfg = CODECS[codec]
    ext = cfg["extension"]
    nums = set()
    try:
        for name in os.listdir(cfg["segments_dir"]):
            if name.endswith(ext):
                try:
                    nums.add(int(name.replace(ext, "")))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    return nums


def get_local_segments(codec: str) -> list[SegmentInfo]:
    now = time.time()
    key = codec + "_local"
    cached = _cache.get(key)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0]

    ffmpeg_segs = parse_ffmpeg_m3u8(codec)
    disk_nums = _scan_disk(codec)
    result = _build_segments(codec, ffmpeg_segs, disk_nums)
    _cache[key] = (result, now)
    return result


def get_all_segments(codec: str) -> list[SegmentInfo]:
    now = time.time()
    cached = _cache.get(codec)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0]

    ffmpeg_segs = parse_ffmpeg_m3u8(codec)
    disk_nums = _scan_disk(codec)

    s3_index = _load_s3_index()
    s3_nums = set()
    if s3_index:
        codec_index = s3_index.get(codec, {})
        for num in codec_index.get("segments", []):
            s3_nums.add(num)

    result = _build_segments(codec, ffmpeg_segs, disk_nums, s3_nums)
    _cache[codec] = (result, now)
    return result


def _get_seg_num(seg: SegmentInfo, ext: str) -> int | None:
    try:
        return int(seg[0].replace(ext, ""))
    except ValueError:
        return None


_live_playlist_cache: dict[str, tuple[str, float]] = {}
_LIVE_PLAYLIST_TTL = 2


def _trim_to_contiguous(segs: list[SegmentInfo], ext: str) -> list[SegmentInfo]:
    """Trim segments to the last contiguous run (no gaps > 2 segment durations).
    This prevents audio glitches from old segments surviving across pod restarts."""
    if len(segs) <= 1:
        return segs
    # Walk backwards from the end, find where a gap starts
    last_contiguous_start = len(segs) - 1
    for i in range(len(segs) - 1, 0, -1):
        cur = _get_seg_num(segs[i], ext)
        prev = _get_seg_num(segs[i - 1], ext)
        if cur is not None and prev is not None and cur - prev > 2:
            break
        last_contiguous_start = i - 1
    return segs[last_contiguous_start:]


def _get_live_playlist(codec: str) -> str | None:
    now = time.time()
    cached = _live_playlist_cache.get(codec)
    if cached and now - cached[1] < _LIVE_PLAYLIST_TTL:
        return cached[0]

    segs = get_local_segments(codec)
    if not segs:
        return None

    ext = CODECS[codec]["extension"]
    # First trim to last contiguous run to avoid gaps from pod restarts
    segs = _trim_to_contiguous(segs, ext)
    # Then apply the live window
    window = segs[-LIVE_WINDOW_SIZE:] if len(segs) > LIVE_WINDOW_SIZE else segs
    playlist = format_playlist(window, codec, server_control=True)
    _live_playlist_cache[codec] = (playlist, now)
    return playlist


def _wait_for_segment(codec: str, msn: int) -> bool:
    ext = CODECS[codec]["extension"]
    deadline = time.time() + BLOCK_TIMEOUT
    while time.time() < deadline:
        _cache.pop(codec + "_local", None)
        segs = get_local_segments(codec)
        if segs:
            last_num = _get_seg_num(segs[-1], ext)
            if last_num is not None and last_num >= msn:
                return True
        time.sleep(0.5)
    return False


def _load_s3_index() -> dict | None:
    global _s3_index_cache, _s3_index_mtime
    try:
        mtime = os.path.getmtime(S3_INDEX_PATH)
        if mtime == _s3_index_mtime and _s3_index_cache is not None:
            return _s3_index_cache
        with open(S3_INDEX_PATH, "r") as f:
            _s3_index_cache = json.load(f)
        _s3_index_mtime = mtime
        return _s3_index_cache
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _find_gaps(nums: list[int], max_gap_segments: int = 3) -> list[dict]:
    gaps = []
    for i in range(1, len(nums)):
        diff = nums[i] - nums[i - 1]
        if diff > max_gap_segments:
            gaps.append({
                "start_epoch": float(nums[i - 1]),
                "end_epoch": float(nums[i]),
                "start_segment": nums[i - 1],
                "end_segment": nums[i],
                "missing_count": diff - 1,
            })
    return gaps


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
    """Generate an EXT-X-DATERANGE tag for a song with rich metadata.

    Embeds: title, artist, thumbnail URL, song_id, station_id so HLS clients
    can display real-time metadata before fetching the full API response.
    """
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


def format_playlist(
    segs: list[SegmentInfo],
    codec: str,
    is_live=True,
    is_event=False,
    skip_count=0,
    server_control=False,
    detect_gaps=True,
) -> str:
    cfg = CODECS[codec]
    prefix = cfg["prefix"]
    init_seg = cfg["init_segment"]
    ext = cfg["extension"]

    if not segs:
        return "#EXTM3U\n#EXT-X-VERSION:9\n#EXT-X-TARGETDURATION:7\n#EXT-X-ENDLIST\n"

    try:
        first_seq = int(segs[0][0].replace(ext, ""))
    except ValueError:
        first_seq = 0

    effective_seq = first_seq - skip_count

    max_dur = max(s[1] for s in segs)
    td = int(max_dur) + 1

    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:9",
        f"#EXT-X-TARGETDURATION:{td}",
        f"#EXT-X-MEDIA-SEQUENCE:{effective_seq}",
        "#EXT-X-INDEPENDENT-SEGMENTS",
    ]

    if server_control:
        lines.append(
            f"#EXT-X-SERVER-CONTROL:CAN-BLOCK-RELOAD=YES,"
            f"CAN-SKIP-UNTIL={SKIP_UNTIL:.1f}"
        )

    if is_event:
        lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")

    if init_seg:
        lines.append(f'#EXT-X-MAP:URI="{init_seg}"')

    if skip_count > 0:
        lines.append(f"#EXT-X-SKIP:SKIPPED-SEGMENTS={skip_count}")

    songs = _get_songs()
    emitted_songs = set()

    prev_num = None
    for fname, dur, pdt in segs:
        cur_num = _get_seg_num((fname, dur, pdt), ext)

        if detect_gaps and prev_num is not None and cur_num is not None:
            diff = cur_num - prev_num
            if diff > 2:
                lines.append("#EXT-X-DISCONTINUITY")

        seg_epoch = _parse_pdt(pdt) if pdt else 0
        if seg_epoch > 0:
            for si, song in enumerate(songs):
                s_start = song.get("started_at", 0)
                if si in emitted_songs:
                    continue
                if s_start >= seg_epoch and s_start < seg_epoch + dur + 1:
                    lines.append(_daterange_for_song(song, si))
                    emitted_songs.add(si)

        if pdt:
            lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{pdt}")
        lines.append(f"#EXTINF:{dur:.6f},")
        lines.append(f"{prefix}{fname}")
        prev_num = cur_num

    if not is_live and not is_event:
        lines.append("#EXT-X-ENDLIST")

    return "\n".join(lines) + "\n"


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
            self._send_m3u8(MASTER_PLAYLIST)
            return
        if parsed.path == "/status.json":
            self._send_status()
            return
        if parsed.path == "/availability.json":
            self._send_availability()
            return

        codec = None
        if parsed.path in ("/aac/index.m3u8", "/index.m3u8"):
            codec = "aac"

        if codec is None:
            self.send_error(404)
            return

        ext = CODECS[codec]["extension"]
        ts_param = params.get("timestamp", [None])[0]
        msn_param = params.get("_HLS_msn", [None])[0]
        skip_param = params.get("_HLS_skip", [None])[0]

        if msn_param is not None:
            try:
                msn = int(msn_param)
            except ValueError:
                self.send_error(400, "Invalid _HLS_msn")
                return

            found = _wait_for_segment(codec, msn)

            segs = get_local_segments(codec)
            if not segs:
                self.send_error(503, "No segments yet")
                return

            # Trim to contiguous run to avoid gaps from pod restarts
            segs = _trim_to_contiguous(segs, ext)

            skip_count = 0
            if skip_param and skip_param.upper() == "YES":
                keep_before = int(SKIP_UNTIL / SEGMENT_DURATION)
                new_segs = []
                for i, s in enumerate(segs):
                    num = _get_seg_num(s, ext)
                    if num is not None and num >= msn - keep_before:
                        skip_count = i
                        new_segs = segs[i:]
                        break
                if not new_segs:
                    new_segs = segs[-LIVE_WINDOW_SIZE:]
                    skip_count = max(0, len(segs) - LIVE_WINDOW_SIZE)
                segs = new_segs
            else:
                if len(segs) > LIVE_WINDOW_SIZE:
                    segs = segs[-LIVE_WINDOW_SIZE:]

            playlist = format_playlist(
                segs, codec,
                is_live=True,
                skip_count=skip_count,
                server_control=True,
                detect_gaps=True,
            )
            self._send_m3u8(playlist)
            return

        if ts_param:
            try:
                target = float(ts_param)
            except ValueError:
                self.send_error(400, "Invalid timestamp")
                return

            segs = get_all_segments(codec)
            if not segs:
                self.send_error(503, "No segments yet")
                return

            oldest = _seg_epoch(segs[0])
            newest = _seg_epoch(segs[-1])
            if target < oldest:
                target = oldest
            if target > newest + 10:
                playlist = format_playlist(
                    segs[-LIVE_WINDOW_SIZE:], codec,
                    server_control=True,
                )
            else:
                idx = next(
                    (i for i, s in enumerate(segs) if _seg_epoch(s) >= target),
                    len(segs),
                )
                window = segs[idx:]
                playlist = format_playlist(
                    window, codec,
                    is_live=False,
                    is_event=True,
                    server_control=True,
                    detect_gaps=True,
                )

            self._send_m3u8(playlist, cache="no-store, must-revalidate")
            return

        playlist = _get_live_playlist(codec)
        if not playlist:
            self.send_error(503, "No segments yet")
            return
        self._send_m3u8(playlist)

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
        }
        for codec in CODECS:
            segs = get_all_segments(codec)
            cfg = CODECS[codec]
            ext = cfg["extension"]
            if segs:
                oldest_pdt = _seg_epoch(segs[0])
                newest_pdt = _seg_epoch(segs[-1])
                nums = []
                for s in segs:
                    try:
                        nums.append(int(s[0].replace(ext, "")))
                    except ValueError:
                        pass
                gaps = _find_gaps(nums)
                result[codec] = {
                    "segments": len(segs),
                    "oldest_epoch": oldest_pdt,
                    "newest_epoch": newest_pdt,
                    "oldest_time": _epoch_to_pdt(oldest_pdt),
                    "newest_time": _epoch_to_pdt(newest_pdt),
                    "duration_seconds": round(newest_pdt - oldest_pdt),
                    "duration_human": _format_duration(newest_pdt - oldest_pdt),
                    "gaps": gaps,
                    "gap_count": len(gaps),
                }
            else:
                result[codec] = {"segments": 0, "gaps": [], "gap_count": 0}

        body = json.dumps(result, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode())

    def _send_availability(self):
        s3_index = _load_s3_index()
        result = {}
        for codec in CODECS:
            local_segs = get_all_segments(codec)
            cfg = CODECS[codec]
            ext = cfg["extension"]

            nums = []
            for s in local_segs:
                try:
                    nums.append(int(s[0].replace(ext, "")))
                except ValueError:
                    pass

            if s3_index and codec in s3_index:
                nums_set = set(nums)
                for n in s3_index[codec].get("segments", []):
                    if n not in nums_set:
                        nums.append(n)
            nums.sort()

            ranges = []
            if nums:
                range_start = nums[0]
                prev = nums[0]
                for n in nums[1:]:
                    if n - prev > 2:
                        ranges.append({
                            "start": float(range_start),
                            "end": float(prev),
                            "start_time": _epoch_to_pdt(float(range_start)),
                            "end_time": _epoch_to_pdt(float(prev)),
                            "segments": prev - range_start + 1,
                        })
                        range_start = n
                    prev = n
                ranges.append({
                    "start": float(range_start),
                    "end": float(prev),
                    "start_time": _epoch_to_pdt(float(range_start)),
                    "end_time": _epoch_to_pdt(float(prev)),
                    "segments": prev - range_start + 1,
                })

            result[codec] = {
                "total_segments": len(nums),
                "ranges": ranges,
                "range_count": len(ranges),
            }

        body = json.dumps(result, indent=2)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body.encode())

    def _send_m3u8(self, body, cache="no-store, must-revalidate"):
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


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _format_duration(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h}h {m}m"


def main():
    port = int(os.environ.get("PLAYLIST_PORT", "8081"))
    server = ThreadingHTTPServer(("127.0.0.1", port), PlaylistHandler)
    print(f"Playlist generator on 127.0.0.1:{port} (threaded)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
