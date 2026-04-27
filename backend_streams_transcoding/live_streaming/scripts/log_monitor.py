"""
NGINX log monitor — tracks listening sessions from HLS request logs.

Tails the NGINX session_access log, parses HLS playlist/segment requests,
batches events every BATCH_INTERVAL seconds, and submits them to Django
via the submit_listening_events GraphQL mutation.

Per-station pod: STATION_SLUG is known from env, no need to parse from URI.
Auth: uses X-Streaming-Api-Key (same as scraper_engine / health_server).
"""

import json
import os
import re
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse

import posthog_reporter

STATION_SLUG = os.environ.get("STATION_SLUG", "")
DJANGO_GRAPHQL_URL = os.environ.get("DJANGO_GRAPHQL_URL", "http://web:8080/v1/graphql")
STREAMING_API_KEY = os.environ.get("STREAMING_POD_API_KEY", "")

LOG_FILE = os.environ.get("NGINX_SESSION_LOG", "/tmp/nginx_session_access.log")
BATCH_INTERVAL = int(os.environ.get("LOG_MONITOR_BATCH_INTERVAL", "10"))

# Regex for the session_access log format defined in nginx.conf
_LOG_RE = re.compile(
    r'(?P<remote_addr>\S+) - (?P<remote_user>\S+) '
    r'\[(?P<time_local>[^\]]+)\] '
    r'"(?P<request>[^"]+)" '
    r'(?P<status>\d+) '
    r'(?P<body_bytes_sent>\d+) '
    r'"(?P<http_referer>[^"]*)" '
    r'"(?P<http_user_agent>[^"]*)" '
    r'session_id="(?P<session_id>[^"]*)" '
    r'ref="(?P<ref>[^"]*)" '
    r'real_ip="(?P<real_ip>[^"]*)" '
    r'cf_ip="(?P<cf_ip>[^"]*)"'
)

_batch_queue = []
_batch_lock = threading.Lock()
_running = True


def _graphql_request(query, variables=None):
    """Execute a GraphQL mutation against Django (same pattern as scraper_engine)."""
    parsed = urlparse(DJANGO_GRAPHQL_URL)
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Streaming-Api-Key": STREAMING_API_KEY,
    }
    try:
        if parsed.scheme == "https":
            conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=15)
        else:
            conn = HTTPConnection(parsed.hostname, parsed.port or 80, timeout=15)
        path = parsed.path or "/"
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        if resp.status in (301, 302, 307, 308):
            location = resp.getheader("Location", "")
            resp.read()
            conn.close()
            redirect_path = urlparse(location).path or path
            if parsed.scheme == "https":
                conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=15)
            else:
                conn = HTTPConnection(parsed.hostname, parsed.port or 80, timeout=15)
            conn.request("POST", redirect_path, body=body, headers=headers)
            resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return data
    except Exception as e:
        print(f"log_monitor: graphql error: {e}", flush=True)
        return None


def _parse_log_line(line):
    """Parse a single NGINX session_access log line. Returns dict or None."""
    m = _LOG_RE.match(line.strip())
    if not m:
        return None

    d = m.groupdict()

    # Only process HLS requests (.m3u8 playlists and .ts segments)
    request_parts = d["request"].split(" ")
    uri = request_parts[1] if len(request_parts) > 1 else "/"
    # Strip query string before checking extension (/index.m3u8?s=abc -> /index.m3u8)
    path = uri.split("?")[0]
    is_playlist = path.endswith(".m3u8")
    is_segment = path.endswith(".ts")
    if not (is_playlist or is_segment):
        return None

    # Must have a session id (the ?s= query param from the client)
    session_id = d["session_id"]
    if not session_id or session_id == "-":
        return None

    # Resolve real client IP: CF-Connecting-IP > X-Forwarded-For > remote_addr
    cf_ip = d.get("cf_ip", "").strip()
    x_fwd = d.get("real_ip", "").strip()
    if cf_ip and cf_ip != "-":
        ip = cf_ip
    elif x_fwd and x_fwd != "-":
        ip = x_fwd.split(",")[0].strip()
    else:
        ip = d["remote_addr"]

    # Referer: prefer ?ref= param, fall back to HTTP Referer header
    ref_param = d.get("ref", "").strip()
    referer = ref_param if ref_param and ref_param != "-" else d["http_referer"]

    try:
        ts = datetime.strptime(d["time_local"], "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        ts = datetime.now(timezone.utc)

    return {
        "session_id": session_id,
        "ip": ip,
        "user_agent": d["http_user_agent"],
        "referer": referer,
        "timestamp": ts.isoformat(),
        "is_playlist": is_playlist,
        "bytes_sent": int(d["body_bytes_sent"]),
        "status": int(d["status"]),
    }


def _submit_batch(events):
    """Submit a batch of listening events to Django."""
    if not events:
        return

    mutation = """
    mutation ($events: [ListeningEventInput!]!) {
        submit_listening_events(events: $events) {
            ... on SubmitListeningEventsResponse {
                __typename
                success
                processed_count
                message
            }
            ... on OperationInfo {
                __typename
                messages { kind message }
            }
        }
    }
    """

    result = _graphql_request(mutation, {"events": events})
    if result:
        data = (result.get("data") or {}).get("submit_listening_events")
        if not data:
            print(f"log_monitor: unexpected response: {result}", flush=True)
            return
        typename = data.get("__typename")
        if typename == "SubmitListeningEventsResponse":
            count = data.get("processed_count", 0)
            print(f"log_monitor: submitted {count}/{len(events)} events", flush=True)
        elif typename == "OperationInfo":
            msgs = data.get("messages", [])
            for msg in msgs:
                print(f"log_monitor: error: {msg.get('kind')} - {msg.get('message')}", flush=True)
        errors = result.get("errors")
        if errors:
            print(f"log_monitor: graphql errors: {errors}", flush=True)


def _process_batch():
    """Consolidate queued events per session and submit."""
    with _batch_lock:
        queue = list(_batch_queue)
        _batch_queue.clear()

    if not queue:
        return

    # Group by session_id, keep latest event per session, sum bytes/counts
    grouped = defaultdict(list)
    for ev in queue:
        grouped[ev["anonymous_session_id"]].append(ev)

    consolidated = []
    for _sid, events in grouped.items():
        latest = max(events, key=lambda e: e["timestamp"])
        latest["bytes_transferred"] = sum(e["bytes_transferred"] for e in events)
        latest["request_count"] = len(events)
        consolidated.append(latest)

    _submit_batch(consolidated)


def _batch_loop():
    """Background thread: flush batch queue every BATCH_INTERVAL seconds."""
    while _running:
        time.sleep(BATCH_INTERVAL)
        if not _running:
            break
        try:
            _process_batch()
        except Exception as e:
            print(f"log_monitor: batch error: {e}", flush=True)


def _tail_log():
    """Poll the NGINX session access log for new lines and enqueue events.

    Uses file-position polling instead of `tail -f` for reliability with
    NGINX's buffered writes inside containers.
    """
    print(f"log_monitor: waiting for {LOG_FILE}...", flush=True)
    while _running and not os.path.exists(LOG_FILE):
        time.sleep(2)

    if not _running:
        return

    print(f"log_monitor: polling {LOG_FILE} (station={STATION_SLUG}, batch={BATCH_INTERVAL}s)", flush=True)

    # Start at the end of the file (only process new lines)
    pos = os.path.getsize(LOG_FILE)

    while _running:
        try:
            size = os.path.getsize(LOG_FILE)
            if size < pos:
                # File was truncated (log rotation), reset
                pos = 0
            if size == pos:
                time.sleep(1)
                continue

            with open(LOG_FILE, "r") as f:
                f.seek(pos)
                new_data = f.read()
                pos = f.tell()

            for line in new_data.splitlines():
                if not line:
                    continue
                parsed = _parse_log_line(line)
                if not parsed:
                    continue

                event = {
                    "anonymous_session_id": parsed["session_id"],
                    "station_slug": STATION_SLUG,
                    "ip_address": parsed["ip"],
                    "user_agent": parsed["user_agent"],
                    "timestamp": parsed["timestamp"],
                    "event_type": "playlist_request" if parsed["is_playlist"] else "segment_request",
                    "bytes_transferred": parsed["bytes_sent"],
                    "request_duration": 0.0,
                    "status_code": parsed["status"],
                    "referer": parsed["referer"],
                }

                with _batch_lock:
                    _batch_queue.append(event)

        except Exception as e:
            print(f"log_monitor: read error: {e}", flush=True)
            time.sleep(2)


def main():
    global _running

    if not STATION_SLUG:
        print("log_monitor: STATION_SLUG not set, exiting", flush=True)
        sys.exit(1)

    if not STREAMING_API_KEY:
        print("log_monitor: STREAMING_POD_API_KEY not set, exiting", flush=True)
        sys.exit(1)

    # Start batch processor thread
    batch_thread = threading.Thread(target=_batch_loop, daemon=True)
    batch_thread.start()

    try:
        _tail_log()
    except KeyboardInterrupt:
        pass
    finally:
        _running = False
        # Flush remaining events
        _process_batch()
        print("log_monitor: shutdown complete", flush=True)


if __name__ == "__main__":
    posthog_reporter.install_global_handler("log_monitor")
    main()
