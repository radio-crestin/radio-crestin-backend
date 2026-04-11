"""
Station listing page — serves an index of all active streaming stations.

Polls the Django GraphQL API for stations with transcoding enabled
and serves an HTML listing page at /.

Runs on port 8080.
"""

import logging
import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("station-listing")

GRAPHQL_ENDPOINT = os.environ.get("GRAPHQL_ENDPOINT", "http://web:8080/v1/graphql")
INGRESS_HOST = os.environ.get("INGRESS_HOST", "live.radiocrestin.ro")
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", "60"))

STATIONS_QUERY = """
query {
    stations(order_by: {order: asc}) {
        slug
        title
        stream_url
        transcode_enabled
    }
}
"""

_stations: list[dict] = []
_html_cache: str = ""


def fetch_stations():
    global _stations, _html_cache
    try:
        resp = requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": STATIONS_QUERY},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            log.error("GraphQL errors: %s", data["errors"])
            return
        all_stations = data.get("data", {}).get("stations", [])
        _stations = [s for s in all_stations if s.get("transcode_enabled")]
        _html_cache = build_html(_stations)
        log.info("Refreshed station list: %d stations", len(_stations))
    except Exception as e:
        log.error("Failed to fetch stations: %s", e)


def build_html(stations):
    rows = []
    for s in stations:
        slug = s["slug"]
        title = s.get("title", slug)
        base = f"https://{INGRESS_HOST}/{slug}"
        rows.append(
            f'<tr>'
            f'<td><a href="{base}/">{title}</a></td>'
            f'<td><code>{slug}</code></td>'
            f'<td><a href="{base}/aac/index.m3u8">AAC+</a></td>'
            f'<td><a href="{base}/opus/index.m3u8">Opus</a></td>'
            f'<td><a href="{base}/master.m3u8">Master</a></td>'
            f'<td><a href="{base}/">Player</a></td>'
            f'</tr>'
        )
    table_rows = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radio Crestin Live Streams</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
  h1 {{ color: #00d4ff; font-size: 22px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
  th {{ text-align: left; padding: 8px 12px; background: #0f3460; color: #888; font-size: 12px; text-transform: uppercase; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #333; }}
  a {{ color: #00d4ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ background: #0a0a1a; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
  .count {{ color: #888; font-size: 14px; margin-left: 8px; }}
</style>
</head>
<body>
<h1>Radio Crestin Live Streams <span class="count">({len(stations)} stations)</span></h1>
<table>
<tr><th>Station</th><th>Slug</th><th>AAC+ HLS</th><th>Opus HLS</th><th>Master</th><th>Player</th></tr>
{table_rows}
</table>
</body>
</html>"""


def refresh_loop():
    while True:
        fetch_stations()
        time.sleep(REFRESH_INTERVAL)


class ListingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=30")
            self.end_headers()
            self.wfile.write((_html_cache or "<h1>Loading...</h1>").encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass


def main():
    log.info("Station listing server starting")
    log.info("GraphQL: %s", GRAPHQL_ENDPOINT)
    log.info("Host: %s", INGRESS_HOST)

    # Initial fetch
    fetch_stations()

    # Background refresh
    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", 8080), ListingHandler)
    log.info("Listening on :8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
