"""
Periodic stream health monitor — emits a one-line digest every MONITOR_INTERVAL
seconds so pod logs reveal *why* clients see HLS stuck-timeout errors.

Surfaces three correlated signals:
  - ffmpeg writing fresh data?  (newest_segment_age, playlist_age, MEDIA-SEQUENCE delta)
  - on-disk retention window?   (segment count, oldest segment age, total disk MB)
  - clients hitting missing files? (segment 404s + playlist 5xx in the last interval)

Logs a separate WARN line whenever any of the above crosses a threshold so the
warnings are easy to grep / alert on without parsing the structured digest.
"""

import glob
import os
import re
import sys
import time

import posthog_reporter

AAC_DIR = "/data/hls/aac"
PLAYLIST = os.path.join(AAC_DIR, "live.m3u8")
SESSION_LOG = os.environ.get("NGINX_SESSION_LOG", "/tmp/nginx_session_access.log")

SEGMENT_DURATION = int(os.environ.get("SEGMENT_DURATION", "6"))
MONITOR_INTERVAL = int(os.environ.get("MONITOR_INTERVAL", "30"))
HLS_LIST_SIZE = int(os.environ.get("HLS_LIST_SIZE", "65"))
# A segment should appear every SEGMENT_DURATION s; flag stalls past 3× that.
STALL_THRESHOLD = SEGMENT_DURATION * 3

_ACCESS_RE = re.compile(r'"(?:GET|HEAD) ([^ ?"]+)[^"]*" (\d{3}) ')


def _segment_stats():
    now = time.time()
    files = glob.glob(os.path.join(AAC_DIR, "*.ts"))
    if not files:
        return {"count": 0, "oldest_s": None, "newest_s": None, "total_mb": 0.0}
    # ffmpeg's delete_segments and cleanup.sh can remove segments between the
    # glob() above and the stat() below. Skip files that vanish mid-iteration
    # rather than crashing the monitor. One stat() per file (vs separate
    # getmtime + getsize) also halves the syscall count.
    mtimes: list[float] = []
    sizes: list[int] = []
    for f in files:
        try:
            st = os.stat(f)
        except FileNotFoundError:
            continue
        mtimes.append(st.st_mtime)
        sizes.append(st.st_size)
    if not mtimes:
        return {"count": 0, "oldest_s": None, "newest_s": None, "total_mb": 0.0}
    return {
        "count": len(mtimes),
        "oldest_s": int(now - min(mtimes)),
        "newest_s": int(now - max(mtimes)),
        "total_mb": round(sum(sizes) / 1_000_000, 1),
    }


def _playlist_stats():
    try:
        st = os.stat(PLAYLIST)
        with open(PLAYLIST, "r") as f:
            text = f.read()
    except FileNotFoundError:
        return {"present": False, "age_s": None, "media_seq": None, "segments": 0}
    seq_match = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", text)
    seg_count = sum(1 for line in text.splitlines() if line.strip().endswith(".ts"))
    return {
        "present": True,
        "age_s": int(time.time() - st.st_mtime),
        "media_seq": int(seq_match.group(1)) if seq_match else None,
        "segments": seg_count,
    }


def _consume_access_log(state):
    """Read new lines since the last tick and tally HLS response codes."""
    counts = {
        "seg_2xx": 0, "seg_404": 0, "seg_5xx": 0,
        "playlist_2xx": 0, "playlist_5xx": 0,
    }
    try:
        size = os.path.getsize(SESSION_LOG)
    except FileNotFoundError:
        return counts
    pos = state.get("log_pos", size)
    if size < pos:
        pos = 0  # rotated/truncated
    if size == pos:
        return counts
    try:
        with open(SESSION_LOG, "r") as f:
            f.seek(pos)
            data = f.read()
            state["log_pos"] = f.tell()
    except OSError:
        return counts
    for line in data.splitlines():
        m = _ACCESS_RE.search(line)
        if not m:
            continue
        path, status = m.group(1), m.group(2)
        if path.endswith(".ts"):
            if status == "404":
                counts["seg_404"] += 1
            elif status.startswith("5"):
                counts["seg_5xx"] += 1
            elif status.startswith("2"):
                counts["seg_2xx"] += 1
        elif path.endswith(".m3u8"):
            if status.startswith("5"):
                counts["playlist_5xx"] += 1
            elif status.startswith("2"):
                counts["playlist_2xx"] += 1
    return counts


def _format_digest(seg, pl, http, seq_advance):
    return (
        "stream_monitor: "
        f"segs={seg['count']} oldest={seg['oldest_s']}s newest={seg['newest_s']}s "
        f"disk={seg['total_mb']}MB | "
        f"playlist={'ok' if pl['present'] else 'missing'} "
        f"age={pl['age_s']}s seq={pl['media_seq']} adv={seq_advance} "
        f"in_pl={pl['segments']} | "
        f"http: pl_2xx={http['playlist_2xx']} pl_5xx={http['playlist_5xx']} "
        f"seg_2xx={http['seg_2xx']} seg_404={http['seg_404']} seg_5xx={http['seg_5xx']}"
    )


def _warnings(seg, pl, http, seq_advance):
    out = []
    if seg["count"] == 0:
        out.append("no segments on disk")
    elif seg["newest_s"] is not None and seg["newest_s"] > STALL_THRESHOLD:
        out.append(f"ffmpeg stalled (newest segment {seg['newest_s']}s old)")
    if pl["present"] and pl["age_s"] is not None and pl["age_s"] > STALL_THRESHOLD:
        out.append(f"playlist stale ({pl['age_s']}s)")
    if not pl["present"]:
        out.append("live.m3u8 missing")
    # Only warn once we're in steady-state — while the playlist is still
    # warming up (segments appending, none removed yet), MEDIA-SEQUENCE
    # legitimately stays put. ffmpeg seeds it from the current epoch
    # (`-hls_start_number_source epoch`), so the previous "media_seq > 0"
    # warmup guard never fires — we use the playlist length instead.
    if (
        seq_advance == 0
        and pl["media_seq"] is not None
        and pl["segments"] is not None
        and pl["segments"] >= HLS_LIST_SIZE
    ):
        out.append(f"MEDIA-SEQUENCE stuck at {pl['media_seq']}")
    if http["seg_404"] > 0:
        out.append(f"{http['seg_404']} segment 404s in interval")
    if http["seg_5xx"] > 0:
        out.append(f"{http['seg_5xx']} segment 5xx in interval")
    if http["playlist_5xx"] > 0:
        out.append(f"{http['playlist_5xx']} playlist 5xx in interval")
    return out


def _report_warnings_to_posthog(warns: list, seg: dict, pl: dict, http: dict, seq_advance):
    """Send each warning as a discrete PostHog event so dashboards can chart
    by warning type per station. Single digest tick → up to N events."""
    if not warns:
        return
    base_props = {
        "segments_on_disk": seg["count"],
        "oldest_segment_age_s": seg["oldest_s"],
        "newest_segment_age_s": seg["newest_s"],
        "playlist_present": pl["present"],
        "playlist_age_s": pl["age_s"],
        "media_seq": pl["media_seq"],
        "media_seq_advance": seq_advance,
        "segments_in_playlist": pl["segments"],
        "segment_404_count": http["seg_404"],
        "segment_5xx_count": http["seg_5xx"],
        "playlist_5xx_count": http["playlist_5xx"],
    }
    for warn in warns:
        # First word of each WARN line is the category (mostly).
        kind = warn.split(" ", 1)[0]
        posthog_reporter.capture_event(
            "stream_warning",
            {**base_props, "warning": warn, "warning_kind": kind},
        )


def main():
    state = {"log_pos": 0, "last_media_seq": None}
    try:
        state["log_pos"] = os.path.getsize(SESSION_LOG)
    except FileNotFoundError:
        state["log_pos"] = 0

    print(
        f"stream_monitor: starting (interval={MONITOR_INTERVAL}s, "
        f"stall_threshold={STALL_THRESHOLD}s, segment_duration={SEGMENT_DURATION}s)",
        flush=True,
    )
    posthog_reporter.capture_event("stream_monitor_started", {
        "interval_s": MONITOR_INTERVAL,
        "stall_threshold_s": STALL_THRESHOLD,
        "segment_duration_s": SEGMENT_DURATION,
    })

    while True:
        time.sleep(MONITOR_INTERVAL)
        seg = _segment_stats()
        pl = _playlist_stats()
        http = _consume_access_log(state)

        seq_advance = None
        if pl["media_seq"] is not None and state["last_media_seq"] is not None:
            seq_advance = pl["media_seq"] - state["last_media_seq"]
        if pl["media_seq"] is not None:
            state["last_media_seq"] = pl["media_seq"]

        print(_format_digest(seg, pl, http, seq_advance), flush=True)
        warns = _warnings(seg, pl, http, seq_advance)
        if warns:
            print(f"stream_monitor: WARN: {'; '.join(warns)}", flush=True)
            try:
                _report_warnings_to_posthog(warns, seg, pl, http, seq_advance)
            except Exception as e:
                print(f"stream_monitor: posthog report failed: {e}", flush=True)


if __name__ == "__main__":
    posthog_reporter.install_global_handler("stream_monitor")
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
