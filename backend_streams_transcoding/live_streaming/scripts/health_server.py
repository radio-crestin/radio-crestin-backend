"""
Health check HTTP server — reports unhealthy when ffmpeg stops producing segments.

Checks:
  1. At least one AAC .ts segment exists and is recent (within HEALTH_MAX_AGE)
  2. Enough segments exist for smooth player handoff (MIN_READY_SEGMENTS)
  3. Every segment referenced in live.m3u8 exists on disk and is non-empty

Returns 200 "ok" when all checks pass, 503 with failure reason otherwise.
Runs on 127.0.0.1:8082.

Also reports health to Django API so the station's uptime record reflects
real FFmpeg status. Reports immediately on startup (is_up=False, starting),
then every REPORT_INTERVAL seconds with current status.
"""

import glob
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
HEALTH_MAX_AGE = int(os.environ.get("HEALTH_MAX_AGE", "30"))
# Minimum local segments before the pod reports ready.
# Ensures players have enough buffer before traffic is switched over.
MIN_READY_SEGMENTS = int(os.environ.get("MIN_READY_SEGMENTS", "3"))
LISTEN_PORT = 8082
REPORT_INTERVAL = int(os.environ.get("HEALTH_REPORT_INTERVAL", "15"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        ok, reason = check_health()
        try:
            if ok:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(503)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(reason.encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, format, *args):
        pass


def _check_segments_fresh():
    """Check that recent .ts segments exist on disk."""
    now = time.time()
    segments = glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts"))
    if not segments:
        return False, "no aac segments on disk"
    newest_mtime = max(os.path.getmtime(s) for s in segments)
    age = now - newest_mtime
    if age > HEALTH_MAX_AGE:
        return False, f"aac segments stale ({int(age)}s old, max {HEALTH_MAX_AGE}s)"
    if len(segments) < MIN_READY_SEGMENTS:
        return False, f"warming up ({len(segments)}/{MIN_READY_SEGMENTS} segments)"
    return True, ""


def _check_playlist_segments():
    """Validate that every segment referenced in live.m3u8 exists on disk and is non-empty."""
    try:
        with open(FFMPEG_PLAYLIST, "r") as f:
            lines = f.read().strip().split("\n")
    except FileNotFoundError:
        return False, "live.m3u8 not found"

    missing = []
    empty = []
    for line in lines:
        if not line.endswith(".ts"):
            continue
        seg_path = os.path.join(AAC_SEGMENTS_DIR, line.strip())
        if not os.path.exists(seg_path):
            missing.append(line.strip())
        elif os.path.getsize(seg_path) == 0:
            empty.append(line.strip())

    if missing:
        return False, f"{len(missing)} segments missing from disk ({missing[0]})"
    if empty:
        return False, f"{len(empty)} segments are empty ({empty[0]})"
    return True, ""


def check_health():
    # 1. Fresh segments on disk
    ok, reason = _check_segments_fresh()
    if not ok:
        return False, reason
    # 2. All playlist segments exist and are non-empty
    ok, reason = _check_playlist_segments()
    if not ok:
        return False, reason
    return True, ""


def _measure_latency():
    """Measure FFmpeg segment production latency (time since newest segment)."""
    try:
        segments = glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts"))
        if not segments:
            return 0
        newest_mtime = max(os.path.getmtime(s) for s in segments)
        return max(0, int((time.time() - newest_mtime) * 1000))
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
    while True:
        time.sleep(REPORT_INTERVAL)
        ok, reason = check_health()
        latency_ms = _measure_latency()
        _report_to_django(
            is_up=ok,
            latency_ms=latency_ms,
            reason=reason if not ok else "ffmpeg producing segments",
        )


if __name__ == "__main__":
    posthog_reporter.install_global_handler("health_server")
    # Start health reporting to Django in background thread
    reporter = threading.Thread(target=_report_health_loop, daemon=True)
    reporter.start()

    server = QuietHTTPServer(("127.0.0.1", LISTEN_PORT), HealthHandler)
    print(f"Health server listening on 127.0.0.1:{LISTEN_PORT} (reporting every {REPORT_INTERVAL}s)")
    server.serve_forever()
