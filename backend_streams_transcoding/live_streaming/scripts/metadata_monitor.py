"""
Song metadata monitor — detects song changes via ICY metadata + silence detection.

Runs FFmpeg with the source stream to extract:
1. ICY metadata (StreamTitle) — authoritative song info from the radio station
2. Silence detection — catches gaps between songs as backup

Writes song history to a 15-minute file tree:
  /data/metadata/index.json              → current song + aggregated info
  /data/metadata/YYYY/MM/DD/HH-MM.json  → songs in that 15-minute window

This process is the only writer of index.json; every write is atomic
(tmp + rename), so readers (playlist_rewriter, scraper_engine) never see a
partial file. A restarted monitor (supervised restart, container restart
with the data volume kept) continues the song timeline from index.json:
the playlists it feeds continue across such restarts too.

A song's `started_at` is the wall-clock time its StreamTitle was read, minus
the station's `id3_metadata_delay_offset` (from station.json, written by
scraper_engine). That one value feeds index.json, the playlist's
EXT-X-DATERANGE / EXT-X-RC-METADATA-CHANGED and the API history, so all of
them describe the same instant.

Runs as a background process alongside the main FFmpeg transcoder.
"""

import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import posthog_reporter
import song_titles

STREAM_URL = os.environ.get("STREAM_URL", "")
METADATA_DIR = Path("/data/metadata")
INDEX_PATH = METADATA_DIR / "index.json"
# {"id3_metadata_delay_offset": float, "config_version": int}, written by
# scraper_engine from the station's Django config.
STATION_CONFIG_PATH = METADATA_DIR / "station.json"

# ffmpeg reports its progress (media time) this often, in seconds.
PROGRESS_PERIOD = 5
# The reader is considered stalled when the media time has not advanced for
# this long. -rw_timeout (10 s) normally ends a stalled read first; this
# also catches a connection that keeps reconnecting without data and a hung
# process. The extractor loop then starts a fresh ffmpeg.
READER_STALL_TIMEOUT = 30
WATCHDOG_INTERVAL = 5
INDEX_HEARTBEAT_INTERVAL = 10
# index.json lists every ended song whose range may still overlap a segment
# of dvr.m3u8: playlist_rewriter keeps segments for DVR_WINDOW_SECONDS +
# 300 s, and a published EXT-X-DATERANGE must stay while it maps to one
# (RFC 8216 4.4.5.1). A fixed song count would drop them early on stations
# that change songs often. The extra minute covers the rewriter's polling.
RECENT_SONGS_MAX_AGE = (
    int(os.environ.get("DVR_WINDOW_SECONDS", "3600")) + 300 + 60)
# Bounds memory on stations whose title changes absurdly often.
SONG_HISTORY_LIMIT = 200

# `-progress` output is `key=value` lines (out_time_us=..., progress=...).
_PROGRESS_LINE = re.compile(r"^[a-z][a-z0-9_]*=")
_MEDIA_TIME = re.compile(r"^out_time_(?:us|ms)=(\d+)$")
_SILENCE = re.compile(r"silencedetect.*silence_start:\s*([\d.]+)")

# Current song state
_current_song = {
    "title": "",
    "artist": "",
    "raw": "",
    "started_at": 0,
    "started_at_iso": "",
}
_song_history: list[dict] = []
_lock = threading.Lock()
# When the stream last delivered media (or a title); see READER_STALL_TIMEOUT.
_reader_alive_at = 0.0
_current_proc: subprocess.Popen | None = None


def _parse_stream_title(raw: str) -> tuple[str, str]:
    """Parse 'Artist - Title' from ICY StreamTitle."""
    raw = raw.strip()
    if not raw:
        return "", ""
    # Common format: "Artist - Title"
    if " - " in raw:
        parts = raw.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "", raw


def song_started_at(detected_at: float, delay_offset: float) -> float:
    """Wall-clock start of a song whose title was read at `detected_at`.

    Detection is 0.03-0.56 s after the audio change in steady state
    (measured). `delay_offset` is the station's id3_metadata_delay_offset:
    positive when its titles arrive late, so the song started earlier.
    """
    return detected_at - delay_offset


def _load_delay_offset() -> float:
    """The station's id3_metadata_delay_offset; 0 until scraper_engine has
    written station.json."""
    try:
        with open(STATION_CONFIG_PATH, "r") as f:
            data = json.load(f)
        return float(data.get("id3_metadata_delay_offset") or 0)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError,
            AttributeError):
        return 0.0


def progress_media_time(line: str) -> int | None:
    """Media time in microseconds from an `out_time_us=` progress line."""
    m = _MEDIA_TIME.match(line)
    return int(m.group(1)) if m else None


def reader_stalled(now: float, alive_at: float) -> bool:
    return now - alive_at > READER_STALL_TIMEOUT


def _mark_alive() -> None:
    global _reader_alive_at
    _reader_alive_at = time.time()


def _write_json_atomic(path: Path, data, indent: int | None = None) -> None:
    """tmp + os.replace: a reader sees the old or the new file, never a
    partial one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=indent)
    os.replace(tmp, path)


def _get_slot_path(epoch: float) -> Path:
    """Get the 15-minute slot file path for a given epoch."""
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    minute_slot = (dt.minute // 15) * 15
    return (
        METADATA_DIR
        / dt.strftime("%Y")
        / dt.strftime("%m")
        / dt.strftime("%d")
        / f"{dt.strftime('%H')}-{minute_slot:02d}.json"
    )


def _load_slot(path: Path) -> list[dict]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_slot(path: Path, songs: list[dict]):
    _write_json_atomic(path, songs, indent=1)


def recent_songs(history: list[dict], now: float) -> list[dict]:
    """The ended songs index.json lists, newest first: every one that ended
    less than RECENT_SONGS_MAX_AGE ago."""
    cutoff = now - RECENT_SONGS_MAX_AGE
    return [song for song in reversed(history)
            if song.get("ended_at", 0) > cutoff]


def _restore_state() -> None:
    """Continue the song timeline of index.json, if there is one.

    The monitor is index.json's only writer, so the file holds exactly the
    state the previous process had. Starting empty instead would remove
    every published EXT-X-DATERANGE while it is still mapped, and the
    connect-time re-announcement of the current title would be dated as a
    new song.
    """
    try:
        with open(INDEX_PATH, "r") as f:
            data = json.load(f)
        current = data.get("current") or {}
        recent = data.get("recent") or []
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return
    if not isinstance(current, dict) or not isinstance(recent, list):
        return
    ended = [s for s in reversed(recent)
             if isinstance(s, dict) and s.get("started_at")]
    restored = bool(current.get("raw") and current.get("started_at"))
    with _lock:
        if restored:
            _current_song.update(current)
        _song_history[:] = ended[-SONG_HISTORY_LIMIT:]
    print(f"metadata: restored {len(ended)} ended songs"
          f"{' and the current one' if restored else ''} from {INDEX_PATH}",
          flush=True)


def _save_index():
    """Write index.json with current song and recent history.

    `monitor_alive_at` lets health_server tell a stalled monitor from a
    station that simply did not change songs.
    """
    with _lock:
        now = time.time()
        data = {
            "current": _current_song.copy(),
            "recent": recent_songs(_song_history, now),
            "updated_at": now,
            "updated_at_iso": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S+0000"
            ),
            "monitor_alive_at": _reader_alive_at,
        }
    try:
        _write_json_atomic(INDEX_PATH, data, indent=1)
    except Exception as e:
        print(f"metadata: index write error: {e}", flush=True)


def _on_song_change(raw_title: str, epoch: float):
    """Handle a song change event."""
    artist, title = _parse_stream_title(raw_title)
    iso = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S+0000"
    )

    song = {
        "title": title,
        "artist": artist,
        "raw": raw_title,
        "started_at": epoch,
        "started_at_iso": iso,
    }

    with _lock:
        # End previous song
        if _current_song["raw"] and _current_song["started_at"] > 0:
            ended = _current_song.copy()
            ended["ended_at"] = epoch
            ended["duration_seconds"] = round(epoch - ended["started_at"])
            _song_history.append(ended)

            # Save to 15-minute slot file
            slot_path = _get_slot_path(ended["started_at"])
            slot = _load_slot(slot_path)
            slot.append(ended)
            _save_slot(slot_path, slot)

            # Keep history bounded
            if len(_song_history) > SONG_HISTORY_LIMIT:
                _song_history[:] = _song_history[-SONG_HISTORY_LIMIT:]

        _current_song.update(song)

    _save_index()
    print(f"metadata: song change: {artist} - {title}", flush=True)


def _on_title(raw_title: str, detected_at: float) -> None:
    """A StreamTitle was read. Only a title different from the current
    song is a song change: ffmpeg re-announces the current title at every
    (re)connect, and dating it again would invent a song boundary."""
    with _lock:
        current = _current_song["raw"]
    if raw_title == current:
        return
    _on_song_change(raw_title,
                    song_started_at(detected_at, _load_delay_offset()))


def _on_silence(epoch: float, duration: float):
    """Handle silence detection (possible song boundary)."""
    # Only log — ICY metadata is the primary song change signal
    print(
        f"metadata: silence at {epoch:.0f} ({duration:.1f}s)",
        flush=True,
    )


def _monitor_ffmpeg_output(proc):
    """Parse FFmpeg stderr for metadata changes and silence events."""
    last_media_us = -1
    for line in proc.stderr:
        line = line.strip()
        if not line:
            continue

        # Progress block: the heartbeat is media time advancing. ffmpeg
        # keeps printing progress while the source is stalled, with the
        # same out_time, so a line alone proves nothing.
        if _PROGRESS_LINE.match(line):
            media_us = progress_media_time(line)
            if media_us is not None and media_us > last_media_us:
                last_media_us = media_us
                _mark_alive()
            continue

        title = song_titles.title_from_ffmpeg_line(line)
        if title is not None:
            _mark_alive()
            _on_title(title, time.time())
            continue

        if _SILENCE.search(line):
            _on_silence(time.time(), 0)


def _ffmpeg_command() -> list[str]:
    return [
        "ffmpeg",
        # Verbose logging required — at default "info" level, FFmpeg only
        # prints ICY StreamTitle at connect time.  Mid-stream ICY metadata
        # updates are only printed at "verbose" level as:
        #   [https @ 0x...] Metadata update for StreamTitle: Artist - Song
        # -nostats drops the \r status line; -progress reports the media
        # time on stderr every PROGRESS_PERIOD s for the heartbeat.
        "-nostats", "-loglevel", "verbose",
        "-progress", "pipe:2", "-stats_period", str(PROGRESS_PERIOD),
        # A stalled read fails after 10 s (µs) and reconnects instead of
        # hanging until the server resets the connection (or forever).
        "-rw_timeout", "10000000",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_on_network_error", "1",
        "-reconnect_delay_max", "30",
        "-i", STREAM_URL,
        # Silence detection filter (low CPU)
        "-af", "silencedetect=noise=-40dB:d=1.5",
        # Null output — we only care about stderr metadata
        "-f", "null", "-",
    ]


def _run_metadata_extractor():
    """Run a lightweight FFmpeg process to monitor stream metadata."""
    global _current_proc
    print(f"metadata: starting monitor for {STREAM_URL}", flush=True)

    while True:
        try:
            # A new process gets the full stall timeout to connect.
            _mark_alive()
            proc = subprocess.Popen(
                _ffmpeg_command(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            _current_proc = proc
            _monitor_ffmpeg_output(proc)
            proc.wait()
            print(f"metadata: ffmpeg exited (code={proc.returncode}), "
                  "restarting in 5s...", flush=True)
        except Exception as e:
            print(f"metadata: error: {e}", flush=True)
        time.sleep(5)


def _watchdog_tick(now: float) -> bool:
    """Kill the reader's ffmpeg when the stream stopped delivering media.
    Returns True when it did."""
    proc = _current_proc
    if proc is None or proc.poll() is not None:
        return False
    if not reader_stalled(now, _reader_alive_at):
        return False
    print(f"metadata: no media for {now - _reader_alive_at:.0f}s, "
          "restarting the reader", flush=True)
    posthog_reporter.capture_event("metadata_reader_stalled", {
        "stalled_s": round(now - _reader_alive_at, 1),
    })
    proc.kill()
    return True


def _watchdog():
    while True:
        time.sleep(WATCHDOG_INTERVAL)
        try:
            _watchdog_tick(time.time())
        except Exception as e:
            print(f"metadata: watchdog error: {e}", flush=True)


def _periodic_index_update():
    """Periodically refresh index.json even without song changes."""
    while True:
        _save_index()
        time.sleep(INDEX_HEARTBEAT_INTERVAL)


def main():
    if not STREAM_URL:
        print("metadata: STREAM_URL not set, exiting", flush=True)
        return

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    # Before the heartbeat's first index.json write.
    _restore_state()
    _mark_alive()

    for target in (_periodic_index_update, _watchdog):
        threading.Thread(target=target, daemon=True).start()

    # Run the metadata extractor (blocks)
    _run_metadata_extractor()


if __name__ == "__main__":
    posthog_reporter.install_global_handler("metadata_monitor")
    main()
