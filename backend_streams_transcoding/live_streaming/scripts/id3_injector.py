"""
ID3 tag injector — prepends ID3v2.4 tags to HLS MPEG-TS segments.

Monitors /data/hls/aac/segments/ for new .ts files and prepends an
ID3v2.4 tag with:
  - TIT2 (title)
  - TPE1 (artist)
  - WXXX (thumbnail URL for real-time display)
  - TXXX (radiocrestin: "Artist - Title", song_id, station_id)

hls.js reads these via Hls.Events.FRAG_PARSING_METADATA.
Per HLS spec (RFC 8216), MPEG-TS segments may contain ID3 metadata.

Supports configurable delay/offset via /data/metadata/index.json
(id3_metadata_delay_offset field, set by scraper_engine from Django config).

Runs as a background process.
"""

import json
import os
import time

SEGMENTS_DIR = "/data/hls/aac/segments"
METADATA_PATH = "/data/metadata/index.json"
POLL_INTERVAL = 1

_processed: set[str] = set()


def _syncsafe_int(n: int) -> bytes:
    """Encode integer as ID3v2 syncsafe (7 bits per byte)."""
    return bytes([
        (n >> 21) & 0x7F,
        (n >> 14) & 0x7F,
        (n >> 7) & 0x7F,
        n & 0x7F,
    ])


def _make_text_frame(frame_id: str, text: str) -> bytes:
    """Build an ID3v2.4 text frame (UTF-8)."""
    encoded = text.encode("utf-8")
    payload = b"\x03" + encoded  # 0x03 = UTF-8 encoding
    size = _syncsafe_int(len(payload))
    return frame_id.encode("ascii") + size + b"\x00\x00" + payload


def _make_wxxx_frame(description: str, url: str) -> bytes:
    """Build an ID3v2.4 WXXX frame (user-defined URL)."""
    payload = b"\x03" + description.encode("utf-8") + b"\x00" + url.encode("utf-8")
    size = _syncsafe_int(len(payload))
    return b"WXXX" + size + b"\x00\x00" + payload


def build_id3_tag(title: str, artist: str, thumbnail_url: str = "",
                  song_id: int = None, station_id: int = None) -> bytes:
    """Build a complete ID3v2.4 tag with metadata frames."""
    frames = b""
    if title:
        frames += _make_text_frame("TIT2", title)
    if artist:
        frames += _make_text_frame("TPE1", artist)
    # TXXX: full "Artist - Title" for simpler client parsing
    if artist and title:
        frames += _make_text_frame("TXXX", f"radiocrestin\x00{artist} - {title}")
    # WXXX: thumbnail URL for real-time display in HLS clients
    if thumbnail_url:
        frames += _make_wxxx_frame("thumbnail", thumbnail_url)
    # TXXX: song_id for direct API lookup
    if song_id:
        frames += _make_text_frame("TXXX", f"song_id\x00{song_id}")
    # TXXX: station_id
    if station_id:
        frames += _make_text_frame("TXXX", f"station_id\x00{station_id}")

    if not frames:
        return b""

    # ID3v2.4 header: "ID3" + version(2,4) + flags(0) + size(syncsafe)
    header = b"ID3\x04\x00\x00" + _syncsafe_int(len(frames))
    return header + frames


def _get_current_song() -> dict:
    """Read current song metadata from index.json."""
    try:
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
        return data.get("current", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def inject_id3():
    """Scan for new .ts segments and prepend ID3 tags."""
    try:
        files = os.listdir(SEGMENTS_DIR)
    except FileNotFoundError:
        return

    song = _get_current_song()
    title = song.get("title", "")
    artist = song.get("artist", "")
    if not title and not artist:
        return

    thumbnail_url = song.get("thumbnail_url", "")
    song_id = song.get("song_id")
    station_id = song.get("station_id")

    id3_tag = build_id3_tag(title, artist, thumbnail_url, song_id, station_id)
    if not id3_tag:
        return

    for name in files:
        if not name.endswith(".ts"):
            continue
        if name in _processed:
            continue

        path = os.path.join(SEGMENTS_DIR, name)
        try:
            with open(path, "rb") as f:
                header = f.read(3)
                if header == b"ID3":
                    _processed.add(name)
                    continue
                f.seek(0)
                original = f.read()

            with open(path, "wb") as f:
                f.write(id3_tag + original)

            _processed.add(name)
        except (FileNotFoundError, PermissionError, OSError):
            pass

    # Prune processed set to avoid memory growth
    if len(_processed) > 500:
        current_files = set(files)
        _processed.intersection_update(current_files)


def main():
    print("ID3 injector: monitoring " + SEGMENTS_DIR, flush=True)
    while True:
        inject_id3()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
