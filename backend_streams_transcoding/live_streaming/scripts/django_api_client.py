"""
Client for the Django API.

Used by health_server to report pod health status to Django.
"""

import json
import os
from http.client import HTTPConnection

DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "web:8080")
STREAMING_POD_API_KEY = os.environ.get("STREAMING_POD_API_KEY", "dev-streaming-key")
STATION_SLUG = os.environ.get("STATION_SLUG", "")

_host, _port = DJANGO_API_URL.split(":") if ":" in DJANGO_API_URL else (DJANGO_API_URL, "8080")
_port = int(_port)


def _request(method, path, body=None):
    """Make an HTTP request to the Django API."""
    try:
        conn = HTTPConnection(_host, _port, timeout=10)
        headers = {
            "X-Streaming-Api-Key": STREAMING_POD_API_KEY,
            "Content-Type": "application/json",
        }

        payload = json.dumps(body).encode() if body else None
        conn.request(method, path, body=payload, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()

        if r.status >= 400:
            print(f"Django API error {method} {path}: {r.status} {data[:200]}", flush=True)
            return None
        return json.loads(data) if data else {}
    except Exception as e:
        print(f"Django API connection error {method} {path}: {e}", flush=True)
        return None


def report_health(is_up, latency_ms=0, reason=""):
    """Report pod health (FFmpeg status) to Django."""
    if not STATION_SLUG:
        return False
    result = _request("POST", "/api/v1/pod-health/", body={
        "station_slug": STATION_SLUG,
        "is_up": is_up,
        "latency_ms": latency_ms,
        "reason": reason,
    })
    return result.get("success", False) if result else False
