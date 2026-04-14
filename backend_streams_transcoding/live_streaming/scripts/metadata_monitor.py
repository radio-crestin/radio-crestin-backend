"""
Song metadata monitor — detects song changes via ICY metadata + silence detection.

Runs FFmpeg with the source stream to extract:
1. ICY metadata (StreamTitle) — authoritative song info from the radio station
2. Silence detection — catches gaps between songs as backup

Writes song history to a 15-minute file tree:
  /data/metadata/index.json              → current song + aggregated info
  /data/metadata/YYYY/MM/DD/HH-MM.json  → songs in that 15-minute window

Runs as a background process alongside the main FFmpeg transcoder.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

STREAM_URL = os.environ.get("STREAM_URL", "")
METADATA_DIR = Path("/data/metadata")
INDEX_PATH = METADATA_DIR / "index.json"

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
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(songs, f, indent=1)


def _save_index():
    """Write index.json with current song and recent history."""
    with _lock:
        data = {
            "current": _current_song.copy(),
            "recent": list(reversed(_song_history[-20:])),
            "updated_at": time.time(),
            "updated_at_iso": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S+0000"
            ),
        }
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(INDEX_PATH, "w") as f:
            json.dump(data, f, indent=1)
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
            if len(_song_history) > 200:
                _song_history[:] = _song_history[-200:]

        _current_song.update(song)

    _save_index()
    print(f"metadata: song change: {artist} - {title}", flush=True)


def _on_silence(epoch: float, duration: float):
    """Handle silence detection (possible song boundary)."""
    # Only log — ICY metadata is the primary song change signal
    print(
        f"metadata: silence at {epoch:.0f} ({duration:.1f}s)",
        flush=True,
    )


def _get_hls_newest_segment_epoch():
    """Get the epoch of the newest segment on disk.

    With clock-aligned segments (segment_atclocktime=1, strftime=%s),
    the segment filename IS the epoch.  Find the newest .ts file.
    """
    seg_dir = "/data/hls/aac/segments"
    try:
        newest = 0
        for name in os.listdir(seg_dir):
            if name.endswith(".ts"):
                try:
                    num = int(name.replace(".ts", ""))
                    if num > newest:
                        newest = num
                except ValueError:
                    pass
        if newest > 0:
            return float(newest)
    except FileNotFoundError:
        pass
    # Fallback to wall clock if no segments yet
    return time.time()


def _monitor_ffmpeg_output(proc):
    """Parse FFmpeg stderr for metadata changes and silence events."""
    last_title = ""
    silence_re = re.compile(
        r"silencedetect.*silence_start:\s*([\d.]+)"
    )
    # Match both formats:
    #   Startup:  "    StreamTitle     : Artist - Song"
    #   Verbose:  "[https @ 0x...] Metadata update for StreamTitle: Artist - Song"
    title_re = re.compile(r"StreamTitle\s*:\s*(.+)")
    metadata_update_re = re.compile(r"Metadata update for StreamTitle:\s*(.+)")

    for line in proc.stderr:
        line = line.strip()
        if not line:
            continue

        # ICY metadata change — verbose format (mid-stream updates)
        m = metadata_update_re.search(line)
        if not m:
            # Fallback: startup format
            m = title_re.search(line)
        if m:
            raw = m.group(1).strip()
            if raw and raw != last_title:
                last_title = raw
                # Use the HLS segment PDT as the authoritative timestamp
                epoch = _get_hls_newest_segment_epoch()
                _on_song_change(raw, epoch)
            continue

        # Silence detection
        m = silence_re.search(line)
        if m:
            _on_silence(time.time(), 0)
            continue


def _run_metadata_extractor():
    """Run a lightweight FFmpeg process to monitor stream metadata."""
    cmd = [
        "ffmpeg",
        # Verbose logging required — at default "info" level, FFmpeg only
        # prints ICY StreamTitle at connect time.  Mid-stream ICY metadata
        # updates are only printed at "verbose" level as:
        #   [https @ 0x...] Metadata update for StreamTitle: Artist - Song
        "-loglevel", "verbose",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "30",
        "-i", STREAM_URL,
        # Silence detection filter (low CPU)
        "-af", "silencedetect=noise=-40dB:d=1.5",
        # Null output — we only care about stderr metadata
        "-f", "null", "-",
    ]

    print(f"metadata: starting monitor for {STREAM_URL}", flush=True)

    while True:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            _monitor_ffmpeg_output(proc)
            proc.wait()
            print("metadata: ffmpeg exited, restarting in 5s...", flush=True)
        except Exception as e:
            print(f"metadata: error: {e}", flush=True)
        time.sleep(5)


def _periodic_index_update():
    """Periodically refresh index.json even without song changes."""
    while True:
        _save_index()
        time.sleep(10)


def _restore_history():
    """Restore song history from index.json written by previous pod (via S3)."""
    global _current_song
    try:
        with open(INDEX_PATH, "r") as f:
            data = json.load(f)
        recent = data.get("recent", [])
        current = data.get("current", {})
        with _lock:
            _song_history.extend(recent)
            if current.get("raw"):
                _current_song.update(current)
        if recent:
            print(f"metadata: restored {len(recent)} songs from previous pod", flush=True)
        if current.get("raw"):
            print(f"metadata: last known song: {current['raw']}", flush=True)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def main():
    if not STREAM_URL:
        print("metadata: STREAM_URL not set, exiting", flush=True)
        return

    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    # Restore history from previous pod (S3 uploader downloads this on startup)
    _restore_history()

    # Start periodic index updates
    t = threading.Thread(target=_periodic_index_update, daemon=True)
    t.start()

    # Run the metadata extractor (blocks)
    _run_metadata_extractor()


if __name__ == "__main__":
    main()
