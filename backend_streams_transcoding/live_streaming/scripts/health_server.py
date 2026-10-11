"""
Health check HTTP server — reports unhealthy when listeners would not get
fresh audio.

Checks:
  1. At least one AAC .ts segment exists and is recent (within HEALTH_MAX_AGE)
  2. Enough segments exist for smooth player handoff (MIN_READY_SEGMENTS)
  3. The playlist listeners get (index.m3u8, written by playlist_rewriter)
     lists at least MIN_READY_SEGMENTS segments, has not fallen behind
     ffmpeg's live.m3u8 for more than HEALTH_MAX_AGE (a stuck or crashed
     rewriter, a boot held back too long; segments it withholds on purpose
     never count), and every segment it lists exists and is non-empty.

GET /health returns 200 "ok" when all checks pass, 503 with failure reason
otherwise; it is the READINESS probe (an upstream outage takes the pod out
of the Service, and ffmpeg_loop reconnects in place).
GET /live always returns 200 "alive": it is the LIVENESS probe and only
proves NGINX and this server answer, so liveness never depends on
upstream. A crashed helper restarts in place (supervisor.sh); NGINX dying
makes the entrypoint exit.
Runs on 127.0.0.1:8082.

Also reports health to Django API so the station's uptime record reflects
real FFmpeg status. Reports immediately on startup (is_up=False, starting),
then every REPORT_INTERVAL seconds with current status. A stalled metadata
monitor is added to that report's reason (and sent to PostHog) without
failing /health: the audio is fine, and a restart would cut listeners off.
"""

import glob
import json
import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import posthog_reporter


class QuietHTTPServer(HTTPServer):
    """HTTPServer that silently ignores BrokenPipe / ConnectionReset.

    kube-probe routinely drops the TCP connection mid-response (probe timeout
    short-circuits, agent moves on). Without this override, every such event
    prints a multi-line traceback to stderr and (worse) trips sys.excepthook,
    flooding both pod logs and PostHog with non-actionable noise.
    """

    def handle_error(self, request, client_address):
        exc_val = sys.exc_info()[1]
        if isinstance(exc_val, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)

AAC_SEGMENTS_DIR = "/data/hls/aac"
FFMPEG_PLAYLIST = os.path.join(AAC_SEGMENTS_DIR, "live.m3u8")
SERVED_PLAYLIST = os.path.join(AAC_SEGMENTS_DIR, "index.m3u8")
# playlist_rewriter's segment history; its unpublished entries are segments
# withheld on purpose (a new ffmpeg run replaying audio already published).
SEGMENT_HISTORY = os.path.join(AAC_SEGMENTS_DIR, "dvr_history.json")
METADATA_INDEX = "/data/metadata/index.json"
HEALTH_MAX_AGE = int(os.environ.get("HEALTH_MAX_AGE", "30"))
# metadata_monitor refreshes monitor_alive_at while the stream delivers
# media; older than this means its reader is stuck.
MONITOR_STALE_AFTER = 60
MONITOR_STALE_REPORT_INTERVAL = 600
# Minimum local segments before the pod reports ready.
# Ensures players have enough buffer before traffic is switched over.
MIN_READY_SEGMENTS = int(os.environ.get("MIN_READY_SEGMENTS", "3"))
LISTEN_PORT = 8082
REPORT_INTERVAL = int(os.environ.get("HEALTH_REPORT_INTERVAL", "15"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/live":
            self._reply(200, b"alive")
        elif self.path == "/health":
            ok, reason = check_health()
            if ok:
                self._reply(200, b"ok")
            else:
                self._reply(503, reason.encode())
        else:
            self._reply(404, b"")

    def _reply(self, status, body):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, format, *args):
        pass


def _newest_mtime(paths):
    """Newest mtime among paths, skipping files deleted while we look.

    cleanup.sh removes segments between glob() and getmtime(); raising
    there turned a healthy probe into a 502.
    """
    newest = 0.0
    for path in paths:
        try:
            newest = max(newest, os.path.getmtime(path))
        except FileNotFoundError:
            continue
    return newest


def _check_segments_fresh():
    """Check that recent .ts segments exist on disk."""
    now = time.time()
    segments = glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts"))
    if not segments:
        return False, "no aac segments on disk"
    newest_mtime = _newest_mtime(segments)
    age = now - newest_mtime
    if age > HEALTH_MAX_AGE:
        return False, f"aac segments stale ({int(age)}s old, max {HEALTH_MAX_AGE}s)"
    if len(segments) < MIN_READY_SEGMENTS:
        return False, f"warming up ({len(segments)}/{MIN_READY_SEGMENTS} segments)"
    return True, ""


def playlist_uris(text: str) -> list[str]:
    """Segment URIs of a media playlist, in order."""
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.startswith("#")]


def served_lag(live_uris: list[str], served: set[str], now: float,
               mtime_of, withheld: frozenset[str] = frozenset()) -> float:
    """Seconds the served playlist has been behind ffmpeg's live.m3u8.

    0 while live.m3u8's newest segment is served. Otherwise the age of the
    first segment ffmpeg listed after the last served or `withheld` one:
    how long listeners have been missing audio that exists. A source stall
    does not count (no new segment exists; check 1 judges it), a hold-back
    after a reconnect burst counts only for itself (at most
    wallclock_pdt.BOOT_ANCHOR_TIMEOUT plus one segment), a stuck rewriter
    grows without bound. Segments the rewriter withholds on purpose (a new
    boot replaying published audio) are never served and never count: a
    deliberate decision must not fail readiness or restart the pod.
    `mtime_of(uri)` is None for a vanished file.
    """
    handled = served | withheld
    if not live_uris or live_uris[-1] in handled:
        return 0.0
    last_handled = max(
        (i for i, uri in enumerate(live_uris) if uri in handled), default=-1)
    for uri in live_uris[last_handled + 1:]:
        mtime = mtime_of(uri)
        if mtime is not None:
            return max(0.0, now - mtime)
    return 0.0


def withheld_segments(history_text: str) -> frozenset[str]:
    """Names of the segments playlist_rewriter's history (dvr_history.json)
    stamped but withheld; empty when the text is not a usable history."""
    try:
        entries = json.loads(history_text).get("entries", [])
        return frozenset(e["name"] for e in entries
                         if e.get("published") is False and "name" in e)
    except (ValueError, AttributeError, TypeError):
        return frozenset()


def _read_withheld() -> frozenset[str]:
    try:
        with open(SEGMENT_HISTORY, "r") as f:
            return withheld_segments(f.read())
    except OSError:
        return frozenset()


def _segment_mtime(uri: str) -> float | None:
    try:
        return os.path.getmtime(os.path.join(AAC_SEGMENTS_DIR, uri))
    except OSError:
        return None


def _check_served_playlist():
    """Validate the playlist listeners get: depth, lag, files."""
    try:
        with open(FFMPEG_PLAYLIST, "r") as f:
            live_uris = playlist_uris(f.read())
    except FileNotFoundError:
        return False, "live.m3u8 not found"
    try:
        with open(SERVED_PLAYLIST, "r") as f:
            served_uris = playlist_uris(f.read())
    except FileNotFoundError:
        return False, "index.m3u8 not found (rewriter has not published)"
    if len(served_uris) < MIN_READY_SEGMENTS:
        return False, (f"warming up ({len(served_uris)}/{MIN_READY_SEGMENTS} "
                       "served segments)")
    lag = served_lag(live_uris, set(served_uris), time.time(),
                     _segment_mtime, _read_withheld())
    if lag > HEALTH_MAX_AGE:
        return False, (f"served playlist {int(lag)}s behind ffmpeg "
                       f"(max {HEALTH_MAX_AGE}s)")

    missing = []
    empty = []
    for uri in served_uris:
        try:
            if os.path.getsize(os.path.join(AAC_SEGMENTS_DIR, uri)) == 0:
                empty.append(uri)
        except OSError:
            missing.append(uri)

    if missing:
        return False, f"{len(missing)} segments missing from disk ({missing[0]})"
    if empty:
        return False, f"{len(empty)} segments are empty ({empty[0]})"
    return True, ""


def metadata_monitor_stalled_for(now: float) -> float | None:
    """Seconds metadata_monitor has gone without media, when that is more
    than MONITOR_STALE_AFTER; None when it is fine or not known yet."""
    try:
        with open(METADATA_INDEX, "r") as f:
            alive_at = json.load(f).get("monitor_alive_at")
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(alive_at, (int, float)) or alive_at <= 0:
        return None
    stalled = now - alive_at
    return stalled if stalled > MONITOR_STALE_AFTER else None


def check_health():
    # 1. Fresh segments on disk
    ok, reason = _check_segments_fresh()
    if not ok:
        return False, reason
    # 2. The served playlist is deep enough, keeps up with ffmpeg and is
    #    fully on disk
    ok, reason = _check_served_playlist()
    if not ok:
        return False, reason
    return True, ""


def _measure_latency():
    """Measure FFmpeg segment production latency (time since newest segment)."""
    try:
        segments = glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts"))
        if not segments:
            return 0
        return max(0, int((time.time() - _newest_mtime(segments)) * 1000))
    except Exception:
        return 0


def _report_to_django(is_up, latency_ms=0, reason=""):
    """Send a single health report to Django."""
    try:
        import django_api_client
        django_api_client.report_health(
            is_up=is_up,
            latency_ms=latency_ms,
            reason=reason,
        )
    except Exception as e:
        print(f"Health report error: {e}", flush=True)


def _report_health_loop():
    """Report FFmpeg health status to Django.

    Reports immediately on startup (is_up=False, starting up), then
    periodically with actual health status. This ensures the station
    uptime reflects the real FFmpeg state from the moment the pod starts.
    """
    # Report starting state immediately
    _report_to_django(is_up=False, reason="pod starting, waiting for ffmpeg")

    # Wait for first segment to appear
    while not glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts")):
        time.sleep(2)

    # Report that FFmpeg is now producing segments
    _report_to_django(is_up=True, latency_ms=_measure_latency(), reason="ffmpeg producing segments")

    # Ongoing periodic reporting
    last_stale_event = 0.0
    while True:
        time.sleep(REPORT_INTERVAL)
        ok, reason = check_health()
        latency_ms = _measure_latency()
        if ok:
            reason = "ffmpeg producing segments"
        now = time.time()
        stalled = metadata_monitor_stalled_for(now)
        if stalled is not None:
            reason += f"; metadata monitor stalled ({int(stalled)}s)"
            if now - last_stale_event >= MONITOR_STALE_REPORT_INTERVAL:
                last_stale_event = now
                posthog_reporter.capture_event("metadata_monitor_stale", {
                    "stalled_s": int(stalled),
                })
        _report_to_django(is_up=ok, latency_ms=latency_ms, reason=reason)


if __name__ == "__main__":
    posthog_reporter.install_global_handler("health_server")
    # Start health reporting to Django in background thread
    reporter = threading.Thread(target=_report_health_loop, daemon=True)
    reporter.start()

    server = QuietHTTPServer(("127.0.0.1", LISTEN_PORT), HealthHandler)
    print(f"Health server listening on 127.0.0.1:{LISTEN_PORT} (reporting every {REPORT_INTERVAL}s)")
    server.serve_forever()
