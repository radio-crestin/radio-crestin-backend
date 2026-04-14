"""
Health check HTTP server — reports unhealthy when ffmpeg stops producing segments.

Checks:
  1. At least one AAC .ts segment exists and is recent

Returns 200 "ok" when all checks pass, 503 with failure reason otherwise.
Runs on 127.0.0.1:8082.

Also reports health to Django API so the station's uptime record reflects
real FFmpeg status. Reports immediately on startup (is_up=False, starting),
then every REPORT_INTERVAL seconds with current status.
"""

import glob
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

AAC_SEGMENTS_DIR = "/data/hls/aac"
HEALTH_MAX_AGE = int(os.environ.get("HEALTH_MAX_AGE", "20"))
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

    def log_message(self, format, *args):
        pass


def _check_dir(directory, extension, label):
    now = time.time()
    segments = glob.glob(os.path.join(directory, f"*{extension}"))
    if not segments:
        return False, f"no {label} segments"
    newest_mtime = max(os.path.getmtime(s) for s in segments)
    age = now - newest_mtime
    if age > HEALTH_MAX_AGE:
        return False, f"{label} segments stale ({int(age)}s old)"
    return True, ""


def check_health():
    ok, reason = _check_dir(AAC_SEGMENTS_DIR, ".ts", "aac")
    if not ok:
        return False, reason
    # Ensure enough segments exist for a smooth player handoff
    segments = glob.glob(os.path.join(AAC_SEGMENTS_DIR, "*.ts"))
    if len(segments) < MIN_READY_SEGMENTS:
        return False, f"warming up ({len(segments)}/{MIN_READY_SEGMENTS} segments)"
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
    # Start health reporting to Django in background thread
    reporter = threading.Thread(target=_report_health_loop, daemon=True)
    reporter.start()

    server = HTTPServer(("127.0.0.1", LISTEN_PORT), HealthHandler)
    print(f"Health server listening on 127.0.0.1:{LISTEN_PORT} (reporting every {REPORT_INTERVAL}s)")
    server.serve_forever()
