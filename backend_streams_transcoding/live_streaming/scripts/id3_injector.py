"""
ID3 tag injector — prepends ID3v2.4 tags to HLS MPEG-TS segments.

Monitors /data/hls/aac/segments/ for new .ts files and prepends an
ID3v2.4 tag with TIT2 (title) and TPE1 (artist) frames read from
/data/metadata/index.json.

hls.js reads these via Hls.Events.FRAG_PARSING_METADATA.
Per HLS spec (RFC 8216), MPEG-TS segments may contain ID3 metadata.

Runs as a background process.
"""

import json
import os
import struct
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
    # Frame: ID(4) + size(4, syncsafe) + flags(2) + encoding(1) + text
    payload = b"\x03" + encoded  # 0x03 = UTF-8 encoding
    size = _syncsafe_int(len(payload))
    return frame_id.encode("ascii") + size + b"\x00\x00" + payload


def _make_priv_frame(owner: str, data: bytes) -> bytes:
    """Build an ID3v2.4 PRIV frame."""
    payload = owner.encode("ascii") + b"\x00" + data
    size = _syncsafe_int(len(payload))
    return b"PRIV" + size + b"\x00\x00" + payload


def build_id3_tag(title: str, artist: str) -> bytes:
    """Build a complete ID3v2.4 tag with TIT2 and TPE1 frames."""
    frames = b""
    if title:
        frames += _make_text_frame("TIT2", title)
    if artist:
        frames += _make_text_frame("TPE1", artist)
    # Add a TXXX frame with the full "Artist - Title" for simpler parsing
    if artist and title:
        frames += _make_text_frame("TXXX", f"radiocrestin\x00{artist} - {title}")

    if not frames:
        return b""

    # ID3v2.4 header: "ID3" + version(2,4) + flags(0) + size(syncsafe)
    header = b"ID3\x04\x00\x00" + _syncsafe_int(len(frames))
    return header + frames


def _get_current_song() -> tuple[str, str]:
    """Read current song from metadata index."""
    try:
        with open(METADATA_PATH, "r") as f:
            data = json.load(f)
        cur = data.get("current", {})
        return cur.get("title", ""), cur.get("artist", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return "", ""


def inject_id3():
    """Scan for new .ts segments and prepend ID3 tags."""
    try:
        files = os.listdir(SEGMENTS_DIR)
    except FileNotFoundError:
        return

    title, artist = _get_current_song()
    if not title and not artist:
        return

    id3_tag = build_id3_tag(title, artist)
    if not id3_tag:
        return

    for name in files:
        if not name.endswith(".ts"):
            continue
        if name in _processed:
            continue

        path = os.path.join(SEGMENTS_DIR, name)
        try:
            # Check if already has ID3 tag (starts with "ID3")
            with open(path, "rb") as f:
                header = f.read(3)
                if header == b"ID3":
                    _processed.add(name)
                    continue
                f.seek(0)
                original = f.read()

            # Prepend ID3 tag
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
