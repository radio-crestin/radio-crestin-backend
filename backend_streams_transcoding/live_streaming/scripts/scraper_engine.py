"""
Pod-side metadata scraper engine.

Fetches scraper configuration from Django GraphQL API on startup.
Runs configured scrapers (shoutcast, icecast, radio_co, etc.) inside the pod.
Reports results back to Django via GraphQL mutation.

Triggered by the station's configured timestamp source:
  - 'mel_analysis': waits for mel_analyzer to write /data/mel_trigger
  - 'id3_metadata': waits for metadata_monitor to detect StreamTitle change
  - 'scraper': runs on a fixed interval (metadata_scrape_interval seconds)

Polls config_version from Django to detect admin changes and reload config.

Memory-efficient: no heavy frameworks, minimal allocations, single-threaded.
"""

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from urllib.parse import urlparse

import posthog_reporter

STATION_SLUG = os.environ.get("STATION_SLUG", "")
DJANGO_GRAPHQL_URL = os.environ.get("DJANGO_GRAPHQL_URL", "http://web:8080/v1/graphql")
STREAMING_API_KEY = os.environ.get("STREAMING_POD_API_KEY", "")

METADATA_INDEX = Path("/data/metadata/index.json")
MEL_TRIGGER = Path("/data/mel_trigger")
ID3_TRIGGER = Path("/data/id3_trigger")
CONFIG_POLL_INTERVAL = 60

# Station config (loaded from Django)
_config = None
_config_version = 0
_last_song_raw = ""


def _graphql_request(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query/mutation against Django."""
    parsed = urlparse(DJANGO_GRAPHQL_URL)
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Streaming-Api-Key": STREAMING_API_KEY,
    }
    try:
        if parsed.scheme == "https":
            conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=10)
        else:
            conn = HTTPConnection(parsed.hostname, parsed.port or 80, timeout=10)
        path = parsed.path or "/"
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        # Follow redirects (Django APPEND_SLASH)
        if resp.status in (301, 302, 307, 308):
            location = resp.getheader("Location", "")
            resp.read()
            conn.close()
            redirect_parsed = urlparse(location)
            redirect_path = redirect_parsed.path or path
            if parsed.scheme == "https":
                conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=10)
            else:
                conn = HTTPConnection(parsed.hostname, parsed.port or 80, timeout=10)
            conn.request("POST", redirect_path, body=body, headers=headers)
            resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        # GraphQL returns {"data": null, "errors": [...]} on failure — the
        # `, {}` default only fires for missing keys, not explicit None values.
        # Use `or {}` so callers can always do data.get(...) without a guard.
        return data.get("data") or {}
    except Exception as e:
        print(f"scraper: graphql error: {e}", flush=True)
        posthog_reporter.capture_exception(e, context={"component": "scraper_engine.graphql"})
        return {}


def _fetch_config() -> dict:
    """Fetch station streaming config from Django."""
    query = """
    query ($slugs: [String!]) {
        streaming_station_configs(station_slugs: $slugs) {
            station_id
            slug
            stream_url
            metadata_timestamp_source
            metadata_scrape_interval
            id3_metadata_delay_offset
            config_version
            scrapers {
                category_slug
                url
                priority
                dirty_metadata
                split_character
                station_name_regex
                artist_regex
                title_regex
            }
        }
    }
    """
    data = _graphql_request(query, {"slugs": [STATION_SLUG]})
    configs = data.get("streaming_station_configs", [])
    if configs:
        return configs[0]
    return {}


def _report_metadata(song_title, song_artist, thumbnail_url=None, listeners=None,
                     raw_title="", timestamp_source="scraper",
                     mel_ts=None, id3_ts=None, scraper_ts=None, dirty=True):
    """Report scraped metadata back to Django."""
    query = """
    mutation ($input: ReportStationMetadataInput!) {
        report_station_metadata(input: $input) {
            ... on ReportStationMetadataResponse {
                success
                message
                song_id
                thumbnail_url
            }
            ... on OperationInfo {
                messages { message kind field }
            }
        }
    }
    """
    variables = {
        "input": {
            "station_slug": STATION_SLUG,
            "song_title": song_title or None,
            "song_artist": song_artist or None,
            "thumbnail_url": thumbnail_url,
            "listeners": listeners,
            "raw_title": raw_title,
            "timestamp_source": timestamp_source,
            "mel_timestamp": mel_ts,
            "id3_timestamp": id3_ts,
            "scraper_timestamp": scraper_ts,
            "dirty_metadata": dirty,
        }
    }
    data = _graphql_request(query, variables)
    result = data.get("report_station_metadata", {})

    # Update local metadata index with song_id and thumbnail from Django
    if result.get("success"):
        _update_local_metadata(
            song_id=result.get("song_id"),
            thumbnail_url=result.get("thumbnail_url"),
            station_id=_config.get("station_id") if _config else None,
        )

    return result


def _update_local_metadata(song_id=None, thumbnail_url=None, station_id=None):
    """Update the local index.json with song_id and thumbnail from Django response."""
    try:
        with open(METADATA_INDEX, "r") as f:
            data = json.load(f)
        changed = False
        cur = data.get("current", {})
        if song_id and cur:
            cur["song_id"] = song_id
            changed = True
        if thumbnail_url and cur:
            cur["thumbnail_url"] = thumbnail_url
            changed = True
        if station_id and cur:
            cur["station_id"] = station_id
            changed = True
        if changed:
            data["current"] = cur
            with open(METADATA_INDEX, "w") as f:
                json.dump(data, f, indent=1)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def _http_get(url: str, timeout: int = 5) -> str:
    """Simple HTTP GET, returns response body as string."""
    parsed = urlparse(url)
    try:
        if parsed.scheme == "https":
            conn = HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout)
        else:
            conn = HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)
        path = parsed.path
        if parsed.query:
            path += "?" + parsed.query
        conn.request("GET", path or "/")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        return body
    except Exception as e:
        print(f"scraper: http error {url}: {e}", flush=True)
        return ""


def _parse_title_artist(raw: str, scraper_cfg: dict) -> tuple:
    """Parse title/artist using the scraper's regex config."""
    if not raw:
        return "", ""

    # Step 1: strip station name
    name_re = scraper_cfg.get("station_name_regex")
    if name_re:
        try:
            raw = re.sub(name_re, "", raw).strip()
        except re.error:
            pass

    # Step 2: regex extraction
    artist_re = scraper_cfg.get("artist_regex")
    title_re = scraper_cfg.get("title_regex")
    if artist_re and title_re:
        try:
            am = re.search(artist_re, raw)
            tm = re.search(title_re, raw)
            if am and tm:
                return am.group(1).strip(), tm.group(1).strip()
        except (re.error, IndexError):
            pass

    # Step 3: split character fallback
    split = scraper_cfg.get("split_character", " - ")
    if split and split in raw:
        parts = raw.split(split, 1)
        return parts[0].strip(), parts[1].strip()

    return "", raw


def _scrape_shoutcast(url: str) -> dict:
    """Scrape Shoutcast JSON stats."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        # v2 JSON format
        if "songtitle" in data:
            return {"raw_title": data["songtitle"], "listeners": data.get("currentlisteners")}
        # v2 with streams array
        streams = data.get("streams", [])
        if streams:
            s = streams[0]
            return {"raw_title": s.get("songtitle", ""), "listeners": s.get("currentlisteners")}
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


def _scrape_icecast(url: str) -> dict:
    """Scrape Icecast JSON stats."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        source = data.get("icestats", {}).get("source", {})
        if isinstance(source, list):
            source = source[0] if source else {}
        return {
            "raw_title": source.get("title", source.get("artist", "")),
            "listeners": source.get("listeners"),
        }
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


def _scrape_radio_co(url: str) -> dict:
    """Scrape radio.co API."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        track = data.get("current_track", {})
        return {
            "raw_title": track.get("title", ""),
            "thumbnail_url": track.get("artwork_url"),
        }
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


def _scrape_shoutcast_xml(url: str) -> dict:
    """Scrape Shoutcast XML stats."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        m = re.search(r"<SONGTITLE>(.*?)</SONGTITLE>", body, re.IGNORECASE)
        listeners_m = re.search(r"<CURRENTLISTENERS>(\d+)</CURRENTLISTENERS>", body, re.IGNORECASE)
        return {
            "raw_title": m.group(1) if m else "",
            "listeners": int(listeners_m.group(1)) if listeners_m else None,
        }
    except (re.error, ValueError):
        pass
    return {}


def _scrape_sonicpanel(url: str) -> dict:
    """Scrape SonicPanel JSON."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        return {
            "raw_title": data.get("title", ""),
            "listeners": data.get("listeners"),
        }
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


def _scrape_aripisprecer(url: str) -> dict:
    """Scrape AripiSpreCer API."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        return {
            "raw_title": f"{data.get('artist', '')} - {data.get('title', '')}",
            "thumbnail_url": data.get("picture"),
        }
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


def _scrape_radio_filadelfia(url: str) -> dict:
    """Scrape Radio Filadelfia API."""
    body = _http_get(url)
    if not body:
        return {}
    try:
        data = json.loads(body)
        return {
            "raw_title": f"{data.get('Artist', '')} - {data.get('Title', '')}",
            "thumbnail_url": data.get("Picture"),
        }
    except (json.JSONDecodeError, KeyError):
        pass
    return {}


SCRAPERS = {
    "shoutcast": _scrape_shoutcast,
    "icecast": _scrape_icecast,
    "radio_co": _scrape_radio_co,
    "shoutcast_xml": _scrape_shoutcast_xml,
    "sonicpanel": _scrape_sonicpanel,
    "aripisprecer_api": _scrape_aripisprecer,
    "radio_filadelfia_api": _scrape_radio_filadelfia,
}


def _run_scrapers(scrapers_config: list) -> dict:
    """Run all configured scrapers in priority order and merge results."""
    results = []
    for cfg in sorted(scrapers_config, key=lambda c: -c.get("priority", 0)):
        slug = cfg.get("category_slug", "")
        # Skip mel_analysis and stream_id3/uptime scrapers — handled separately
        if slug in ("mel_analysis", "stream_id3", "uptime_ffmpeg", "uptime_http",
                     "old_icecast_html", "old_shoutcast_html"):
            continue
        scraper_fn = SCRAPERS.get(slug)
        if not scraper_fn:
            continue
        url = cfg.get("url", "")
        if not url:
            continue
        raw_result = scraper_fn(url)
        if not raw_result or not raw_result.get("raw_title"):
            continue

        # Some upstream APIs (e.g. Shoutcast servers populating `songtitle`
        # with a numeric song-id, Icecast variants with int `title` fields)
        # return non-string values. Coerce once at the boundary so every
        # downstream string operation is safe.
        raw_title = str(raw_result["raw_title"]).strip()
        if not raw_title:
            continue

        artist, title = _parse_title_artist(raw_title, cfg)
        results.append({
            "raw_title": raw_title,
            "title": title,
            "artist": artist,
            "thumbnail_url": raw_result.get("thumbnail_url"),
            "listeners": raw_result.get("listeners"),
            "priority": cfg.get("priority", 0),
            "dirty": cfg.get("dirty_metadata", True),
        })

    if not results:
        return {}

    # Merge by priority: highest priority first, fill missing fields from lower
    merged = results[0].copy()
    for r in results[1:]:
        if not merged.get("title") and r.get("title"):
            merged["title"] = r["title"]
            merged["artist"] = r.get("artist", "")
        if not merged.get("thumbnail_url") and r.get("thumbnail_url"):
            merged["thumbnail_url"] = r["thumbnail_url"]
        if merged.get("listeners") is None and r.get("listeners") is not None:
            merged["listeners"] = r["listeners"]
    return merged


def _check_trigger(trigger_path: Path) -> str:
    """Check if a trigger file exists and return its content, then delete it."""
    try:
        content = trigger_path.read_text().strip()
        trigger_path.unlink(missing_ok=True)
        return content
    except FileNotFoundError:
        return ""


def _get_id3_song() -> str:
    """Read current song from metadata_monitor's index.json."""
    try:
        with open(METADATA_INDEX, "r") as f:
            data = json.load(f)
        return data.get("current", {}).get("raw", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _get_id3_started_at() -> float:
    """Read the stream-accurate started_at epoch from metadata_monitor."""
    try:
        with open(METADATA_INDEX, "r") as f:
            data = json.load(f)
        return data.get("current", {}).get("started_at", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def main():
    global _config, _config_version, _last_song_raw

    if not STATION_SLUG:
        print("scraper: STATION_SLUG not set, exiting", flush=True)
        return

    print(f"scraper: starting for {STATION_SLUG}", flush=True)

    # Wait for Django to be available
    while not _config:
        _config = _fetch_config()
        if not _config:
            print("scraper: waiting for Django config...", flush=True)
            time.sleep(10)
            continue
        _config_version = _config.get("config_version", 0)
        print(f"scraper: loaded config v{_config_version}, "
              f"source={_config.get('metadata_timestamp_source')}, "
              f"interval={_config.get('metadata_scrape_interval')}s, "
              f"scrapers={len(_config.get('scrapers', []))}", flush=True)

    last_scrape_time = 0
    last_config_check = time.time()
    ts_source = _config.get("metadata_timestamp_source", "scraper")
    interval = _config.get("metadata_scrape_interval", 30)

    while True:
        now = time.time()

        # Periodically check for config changes
        if now - last_config_check > CONFIG_POLL_INTERVAL:
            new_config = _fetch_config()
            if new_config and new_config.get("config_version", 0) > _config_version:
                _config = new_config
                _config_version = new_config["config_version"]
                ts_source = _config.get("metadata_timestamp_source", "scraper")
                interval = _config.get("metadata_scrape_interval", 30)
                print(f"scraper: config updated to v{_config_version}", flush=True)
            last_config_check = now

        should_scrape = False
        mel_ts = None
        id3_ts = None
        scraper_ts = None

        if ts_source == "mel_analysis":
            trigger = _check_trigger(MEL_TRIGGER)
            if trigger:
                should_scrape = True
                mel_ts = trigger  # ISO timestamp from mel analyzer
                print(f"scraper: mel trigger received", flush=True)

        elif ts_source == "id3_metadata":
            current_raw = _get_id3_song()
            if current_raw and current_raw != _last_song_raw:
                _last_song_raw = current_raw
                should_scrape = True
                # Use stream-accurate timestamp from metadata_monitor
                stream_epoch = _get_id3_started_at()
                if stream_epoch > 0:
                    offset = _config.get("id3_metadata_delay_offset", 0)
                    id3_epoch = stream_epoch - offset
                else:
                    offset = _config.get("id3_metadata_delay_offset", 0)
                    id3_epoch = now - offset
                from datetime import datetime, timezone as dt_tz
                id3_ts = datetime.fromtimestamp(id3_epoch, tz=dt_tz.utc).isoformat()
                print(f"scraper: id3 trigger: {current_raw}", flush=True)

        else:  # scraper (periodic)
            if now - last_scrape_time >= interval:
                should_scrape = True
                from datetime import datetime, timezone as dt_tz
                # Use the stream-accurate timestamp from metadata_monitor
                # if available (when FFmpeg ICY metadata detected the song)
                stream_epoch = _get_id3_started_at()
                if stream_epoch > 0:
                    scraper_ts = datetime.fromtimestamp(stream_epoch, tz=dt_tz.utc).isoformat()
                else:
                    scraper_ts = datetime.fromtimestamp(now, tz=dt_tz.utc).isoformat()

        if should_scrape:
            scrapers = _config.get("scrapers", [])
            result = _run_scrapers(scrapers)

            # Fallback: if external scrapers returned nothing, use ICY metadata
            if not result:
                icy_song = _get_id3_song()
                if icy_song:
                    artist, title = "", icy_song
                    if " - " in icy_song:
                        parts = icy_song.split(" - ", 1)
                        artist, title = parts[0].strip(), parts[1].strip()
                    result = {
                        "title": title,
                        "artist": artist,
                        "raw_title": icy_song,
                        "dirty": True,
                    }

            if result:
                resp = _report_metadata(
                    song_title=result.get("title"),
                    song_artist=result.get("artist"),
                    thumbnail_url=result.get("thumbnail_url"),
                    listeners=result.get("listeners"),
                    raw_title=result.get("raw_title", ""),
                    timestamp_source=ts_source,
                    mel_ts=mel_ts,
                    id3_ts=id3_ts,
                    scraper_ts=scraper_ts,
                    dirty=result.get("dirty", True),
                )
                if resp.get("success"):
                    print(f"scraper: reported '{result.get('artist', '')} - {result.get('title', '')}'", flush=True)

            last_scrape_time = now

        # Sleep interval depends on timestamp source
        if ts_source == "mel_analysis":
            time.sleep(1)  # Poll mel trigger frequently
        elif ts_source == "id3_metadata":
            time.sleep(2)  # Poll id3 changes
        else:
            time.sleep(min(interval, 5))  # Don't sleep longer than 5s for responsiveness


if __name__ == "__main__":
    posthog_reporter.install_global_handler("scraper_engine")
    main()
