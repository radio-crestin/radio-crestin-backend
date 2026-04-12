"""
Health check HTTP server — reports unhealthy when ffmpeg stops producing segments.

Checks:
  1. At least one AAC .ts segment exists and is recent

Returns 200 "ok" when all checks pass, 503 with failure reason otherwise.
Runs on 127.0.0.1:8082.
"""

import glob
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

AAC_SEGMENTS_DIR = "/data/hls/aac/segments"
HEALTH_MAX_AGE = int(os.environ.get("HEALTH_MAX_AGE", "20"))
LISTEN_PORT = 8082


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
    return True, ""


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", LISTEN_PORT), HealthHandler)
    print(f"Health server listening on 127.0.0.1:{LISTEN_PORT}")
    server.serve_forever()
