"""
Pod-side metadata scraper engine.

Fetches scraper configuration from Django GraphQL API on startup.
Runs configured scrapers (shoutcast, icecast, radio_co, etc.) inside the pod.
Reports results back to Django via GraphQL mutation.

Triggered by the station's configured timestamp source:
  - 'id3_metadata': waits for metadata_monitor to detect StreamTitle change
  - 'scraper' (and any unknown source): runs on a fixed interval
    (metadata_scrape_interval seconds)

Polls config_version from Django to detect admin changes and reload config.

Files under /data/metadata (all written atomically):
  - index.json        read only; metadata_monitor is its single writer.
  - station.json      the config metadata_monitor needs (the delay offset).
  - now_playing.json  the song Django accepted for the current ICY song
                      instance; playlist_rewriter turns it into the X-*
                      hints of EXT-X-RC-METADATA-CHANGED.

Memory-efficient: no heavy frameworks, minimal allocations, single-threaded.
"""

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlparse

import posthog_reporter
import song_titles

STATION_SLUG = os.environ.get("STATION_SLUG", "")
DJANGO_GRAPHQL_URL = os.environ.get("DJANGO_GRAPHQL_URL", "http://web:8080/v1/graphql")
STREAMING_API_KEY = os.environ.get("STREAMING_POD_API_KEY", "")

METADATA_INDEX = Path("/data/metadata/index.json")
STATION_CONFIG_PATH = Path("/data/metadata/station.json")
NOW_PLAYING_PATH = Path("/data/metadata/now_playing.json")
ID3_TRIGGER = Path("/data/id3_trigger")
CONFIG_POLL_INTERVAL = 60

# Station config (loaded from Django)
_config = None
_config_version = 0
_last_song_raw = ""
# (raw, started_at, song_id) of the song instance now_playing.json holds.
_now_playing_key = None


def _parse_graphql_response(status: int, raw: bytes) -> dict:
    """Parse a GraphQL HTTP response body into its ``data`` payload.

    See _parse_graphql_body(); this drops the errors.
    """
    return _parse_graphql_body(status, raw)[0]


def _parse_graphql_body(status: int, raw: bytes) -> tuple[dict, list]:
    """Parse a GraphQL HTTP response body into ``(data, errors)``.

    Returns ``{}`` (instead of raising) when the upstream returns a non-2xx
    status or a body that isn't valid JSON. Django behind nginx can answer with
    an HTML error page (e.g. 502/503 during a restart/deploy); previously
    ``json.loads()`` raised ``JSONDecodeError: Expecting value: line 1 column 1
    (char 0)`` which was reported to PostHog as noise. Treat those as a
    transient empty result.
    """
    if status >= 400:
        print(f"scraper: graphql HTTP {status}: {raw[:200]!r}", flush=True)
        return {}, []
    if not raw or not raw.strip():
        return {}, []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print(
            f"scraper: graphql non-JSON response (HTTP {status}): {raw[:200]!r}",
            flush=True,
        )
        return {}, []
    if not isinstance(data, dict):
        return {}, []
    errors = data.get("errors")
    # GraphQL returns {"data": null, "errors": [...]} on failure — `or {}` lets
    # callers always do data.get(...) without a guard.
    return data.get("data") or {}, errors if isinstance(errors, list) else []


def _graphql_request(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query/mutation against Django."""
    return _graphql_call(query, variables)[0]


def _graphql_call(query: str, variables: dict = None) -> tuple[dict, list]:
    """Execute a GraphQL query/mutation; ``(data, errors)``."""
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
        raw = resp.read()
        conn.close()
        return _parse_graphql_body(resp.status, raw)
    except Exception as e:
        print(f"scraper: graphql error: {e}", flush=True)
        posthog_reporter.capture_exception(e, context={"component": "scraper_engine.graphql"})
        return {}, []


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


# The song as Django stored it, for the playlist hint. Requested only while
# Django knows the fields: a pod may start before the Django release that
# adds them, and an unknown field fails the whole mutation at validation
# (nothing executes).
_REPORT_FIELDS = """
                success
                message
                song_id
                thumbnail_url"""
_REPORT_SONG_FIELDS = """
                song_title
                song_artist
                song_artist_id
                song_thumbnail_url
                history_timestamp"""
# After Django rejected them, ask again this much later (Django may have
# been deployed meanwhile; the pod is not restarted for that).
SONG_FIELDS_RETRY_INTERVAL = 3600
_song_fields_retry_at = 0.0


def _report_mutation(song_fields: bool) -> str:
    fields = _REPORT_FIELDS + (_REPORT_SONG_FIELDS if song_fields else "")
    return f"""
    mutation ($input: ReportStationMetadataInput!) {{
        report_station_metadata(input: $input) {{
            ... on ReportStationMetadataResponse {{{fields}
            }}
            ... on OperationInfo {{
                messages {{ message kind field }}
            }}
        }}
    }}
    """


def _unknown_field_error(errors: list) -> bool:
    return any("Cannot query field" in str(e.get("message", ""))
               for e in errors if isinstance(e, dict))


def _report_metadata(song_title, song_artist, thumbnail_url=None, listeners=None,
                     raw_title="", timestamp_source="scraper",
                     id3_ts=None, scraper_ts=None, dirty=True):
    """Report scraped metadata back to Django; the response dict."""
    global _song_fields_retry_at
    variables = {
        "input": {
            "station_slug": STATION_SLUG,
            "song_title": song_title or None,
            "song_artist": song_artist or None,
            "thumbnail_url": thumbnail_url,
            "listeners": listeners,
            "raw_title": raw_title,
            "timestamp_source": timestamp_source,
            "id3_timestamp": id3_ts,
            "scraper_timestamp": scraper_ts,
            "dirty_metadata": dirty,
        }
    }
    song_fields = time.time() >= _song_fields_retry_at
    data, errors = _graphql_call(_report_mutation(song_fields), variables)
    if not data and song_fields and _unknown_field_error(errors):
        print("scraper: Django predates the song fields of "
              "ReportStationMetadataResponse; reporting without them",
              flush=True)
        _song_fields_retry_at = time.time() + SONG_FIELDS_RETRY_INTERVAL
        data, errors = _graphql_call(_report_mutation(False), variables)
    return data.get("report_station_metadata") or {}


def _write_json_atomic(path: Path, data) -> None:
    """tmp + os.replace: readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _write_station_config(config: dict) -> None:
    """Hand metadata_monitor the config it needs to date songs: it subtracts
    id3_metadata_delay_offset from every ICY detection."""
    try:
        _write_json_atomic(STATION_CONFIG_PATH, {
            "id3_metadata_delay_offset":
                float(config.get("id3_metadata_delay_offset") or 0),
            "config_version": config.get("config_version", 0),
        })
    except (OSError, TypeError, ValueError) as e:
        print(f"scraper: station.json write error: {e}", flush=True)


def _remember_report(icy, response: dict, now: float) -> None:
    """Publish the accepted song for the playlist hints, or withdraw them.

    `icy` is the ICY song instance (index.json `current`) that dated the
    report, or None when it was dated otherwise: then the reported song is
    not known to be the song that started at the playlist's EPOCH, and any
    previous hint is removed. Only the song as Django returned it is
    written, so the hint equals what the API serves.
    """
    global _now_playing_key
    song_id = response.get("song_id")
    if icy is None or not song_id:
        _now_playing_key = None
        try:
            NOW_PLAYING_PATH.unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            print(f"scraper: now_playing.json remove error: {e}", flush=True)
        return
    key = (icy.raw, icy.started_at, song_id)
    if key == _now_playing_key:
        return
    try:
        _write_json_atomic(NOW_PLAYING_PATH, {
            "raw": icy.raw,
            "started_at": icy.started_at,
            "title": response.get("song_title"),
            "artist": response.get("song_artist"),
            "song_id": song_id,
            "song_artist_id": response.get("song_artist_id"),
            "song_thumbnail_url": response.get("song_thumbnail_url"),
            "history_timestamp": response.get("history_timestamp"),
            "reported_at": now,
        })
        _now_playing_key = key
    except OSError as e:
        print(f"scraper: now_playing.json write error: {e}", flush=True)


def _http_get(url: str, timeout: int = 5) -> str:
    """Simple HTTP GET, returns response body as string (also on an error status).
    urllib honours HTTP(S)_PROXY / NO_PROXY, i.e. the pod's egress sidecar;
    a bare http.client connection would go straight out and be dropped."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", errors="replace")
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
        # Skip stream_id3/uptime/legacy scrapers — handled separately or not used
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
        # downstream string operation is safe; placeholders ("-", "N/A")
        # and ffmpeg/decoder messages are not titles at all.
        raw_title = song_titles.clean_title(raw_result["raw_title"])
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


@dataclass(frozen=True)
class IcySong:
    """metadata_monitor's current song: its raw ICY title and wall-clock
    start (offset-corrected)."""

    raw: str
    started_at: float


def _get_icy_current() -> IcySong | None:
    """The current song of index.json, read once so title and start belong
    to the same song instance."""
    try:
        with open(METADATA_INDEX, "r") as f:
            current = json.load(f).get("current") or {}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None
    raw = current.get("raw") or ""
    if not raw:
        return None
    try:
        started_at = float(current.get("started_at") or 0)
    except (TypeError, ValueError):
        started_at = 0.0
    return IcySong(raw, started_at)


@dataclass(frozen=True)
class Dating:
    """The timestamp of one scraper-mode report and where it came from.

    `icy` is the ICY song instance whose start dates the reported song, or
    None when the song is dated by the scrape. `scrape_dated_change` marks a
    song change dated by the scrape although an earlier change exists to
    compare with (the rate is reported to PostHog).
    """

    timestamp: float
    song_changed: bool
    icy: IcySong | None
    scrape_dated_change: bool = False


class ReportClock:
    """Dates scraper-mode reports.

    A song change is dated by the ICY start whenever ICY changed since the
    last reported song change, even when the scraped title differs from the
    ICY title (sources format the same song differently, and a scrape can
    lag the stream by a whole interval): the API row then lands at the
    playlist's EPOCH instead of up to one scrape interval later. Only when
    ICY did not change (a static or missing ICY title) is the song dated by
    the scrape that first saw it. An unchanged song resends the timestamp of
    its change; Django dates listener-count updates itself.

    The first report has nothing to compare ICY with and is dated by the
    scrape.
    """

    def __init__(self):
        self._raw: str | None = None
        self._dating: Dating | None = None
        self._icy_seen: IcySong | None = None

    def date(self, raw_title: str, icy: IcySong | None,
             now: float) -> Dating:
        if self._dating is not None and raw_title == self._raw:
            return Dating(self._dating.timestamp, False, self._dating.icy)
        first = self._dating is None
        icy_changed = (not first and icy is not None and icy.started_at > 0
                       and icy != self._icy_seen)
        if icy_changed:
            dating = Dating(icy.started_at, True, icy)
        else:
            dating = Dating(now, True, None, scrape_dated_change=not first)
        self._raw, self._dating, self._icy_seen = raw_title, dating, icy
        return dating


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _icy_result(raw: str) -> dict:
    """A report built from the ICY title alone (no scraper answered)."""
    artist, title = "", raw
    if " - " in raw:
        artist, title = (part.strip() for part in raw.split(" - ", 1))
    return {"title": title, "artist": artist, "raw_title": raw, "dirty": True}


def _send_report(result: dict, timestamp_source: str, id3_ts=None,
                 scraper_ts=None) -> dict:
    response = _report_metadata(
        song_title=result.get("title"),
        song_artist=result.get("artist"),
        thumbnail_url=result.get("thumbnail_url"),
        listeners=result.get("listeners"),
        raw_title=result.get("raw_title", ""),
        timestamp_source=timestamp_source,
        id3_ts=id3_ts,
        scraper_ts=scraper_ts,
        dirty=result.get("dirty", True),
    )
    if response.get("success"):
        print(f"scraper: reported '{result.get('artist', '')} - "
              f"{result.get('title', '')}'", flush=True)
    return response


def _report_icy_change(icy: IcySong, now: float) -> None:
    """id3_metadata mode: ICY announced a new song. It is dated by its ICY
    start, which metadata_monitor already corrected by the delay offset."""
    result = _run_scrapers(_config.get("scrapers", [])) or _icy_result(icy.raw)
    if icy.started_at > 0:
        epoch = icy.started_at
    else:  # no ICY start known: the detection is now
        epoch = now - float(_config.get("id3_metadata_delay_offset") or 0)
    response = _send_report(result, "id3_metadata", id3_ts=_iso(epoch))
    if response.get("success"):
        _remember_report(icy if icy.started_at > 0 else None, response, now)


def _scrape_and_report(clock: ReportClock, timestamp_source: str,
                       now: float) -> None:
    """Scraper mode: one periodic scrape and its report."""
    icy = _get_icy_current()
    result = _run_scrapers(_config.get("scrapers", []))
    if not result and icy is not None:
        result = _icy_result(icy.raw)
    if not result:
        return
    dating = clock.date(result["raw_title"], icy, now)
    if dating.scrape_dated_change:
        posthog_reporter.capture_event("scrape_dated_song_change", {
            "timestamp_source": timestamp_source,
            "icy_known": icy is not None and icy.started_at > 0,
        })
    response = _send_report(result, timestamp_source,
                            scraper_ts=_iso(dating.timestamp))
    if response.get("success"):
        _remember_report(dating.icy, response, now)


def _load_config(config: dict) -> None:
    global _config, _config_version
    _config = config
    _config_version = config.get("config_version", 0)
    _write_station_config(config)


def main():
    global _last_song_raw

    if not STATION_SLUG:
        print("scraper: STATION_SLUG not set, exiting", flush=True)
        return

    print(f"scraper: starting for {STATION_SLUG}", flush=True)

    # Wait for Django to be available
    while not _config:
        config = _fetch_config()
        if not config:
            print("scraper: waiting for Django config...", flush=True)
            time.sleep(10)
            continue
        _load_config(config)
        print(f"scraper: loaded config v{_config_version}, "
              f"source={_config.get('metadata_timestamp_source')}, "
              f"interval={_config.get('metadata_scrape_interval')}s, "
              f"scrapers={len(_config.get('scrapers', []))}", flush=True)

    last_scrape_time = 0
    last_config_check = time.time()
    ts_source = _config.get("metadata_timestamp_source", "scraper")
    interval = _config.get("metadata_scrape_interval", 30)
    clock = ReportClock()

    while True:
        now = time.time()

        # Periodically check for config changes
        if now - last_config_check > CONFIG_POLL_INTERVAL:
            new_config = _fetch_config()
            if new_config and new_config.get("config_version", 0) > _config_version:
                _load_config(new_config)
                ts_source = _config.get("metadata_timestamp_source", "scraper")
                interval = _config.get("metadata_scrape_interval", 30)
                print(f"scraper: config updated to v{_config_version}", flush=True)
            last_config_check = now

        if ts_source == "id3_metadata":
            icy = _get_icy_current()
            if icy is not None and icy.raw != _last_song_raw:
                _last_song_raw = icy.raw
                print(f"scraper: id3 trigger: {icy.raw}", flush=True)
                _report_icy_change(icy, now)
            time.sleep(2)  # Poll id3 changes
        else:  # scraper (periodic) — also catches any unknown/legacy ts_source
            if now - last_scrape_time >= interval:
                _scrape_and_report(clock, ts_source, now)
                last_scrape_time = now
            time.sleep(min(interval, 5))  # Don't sleep longer than 5s for responsiveness


if __name__ == "__main__":
    posthog_reporter.install_global_handler("scraper_engine")
    main()
