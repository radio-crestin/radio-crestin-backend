"""
Song-title hygiene shared by metadata_monitor and scraper_engine.

* `title_from_ffmpeg_line` reads a StreamTitle out of ffmpeg's stderr. The
  dump line ("    StreamTitle     : <value>") is matched only at the start of
  a line: ffmpeg continues a log line without its "[ctx @ 0x..]" prefix when
  the previous message had no newline, which is how the AAC decoder error
  "ChannelElement 3.1 missing" became alt-fm's song title on 2026-09-02.
* `clean_title` rejects values that are not song titles at all.
* `titles_match` decides whether a scraped title is the song ICY announced,
  which tells scraper_engine whether ICY's start time dates that song.
"""

from __future__ import annotations

import re
import unicodedata

_UPDATE_RE = re.compile(r"Metadata update for StreamTitle:\s*(.*)$")
_DUMP_RE = re.compile(r"^\s*StreamTitle\s*:\s*(.*)$")

# ffmpeg messages that can end up after "StreamTitle :" on one line.
_FFMPEG_MESSAGES = (
    # "[aac @ 0x55d5c8a3e2c0]": a context and its address, which is 0x-hex
    # or 16 bare hex digits (Windows), so "[Live @ 2024] Isus" is a title.
    re.compile(r"^\[[\w:.-]+ @ (0x[0-9a-fA-F]+|[0-9a-fA-F]{16})\]"),
    re.compile(r"\bChannelElement \d+\.\d+ missing\b", re.IGNORECASE),
    re.compile(r"\bchannel element \d+\.\d+ (is not allocated|duplicate)\b",
               re.IGNORECASE),
    re.compile(r"\b(Error while decoding|Invalid data found when processing input)\b",
               re.IGNORECASE),
)
_PLACEHOLDERS = {"", "-", "--", "n/a", "na", "null", "none", "undefined"}


def clean_title(raw: object) -> str | None:
    """The title with whitespace collapsed, or None if it is not a title."""
    if raw is None:
        return None
    text = " ".join(str(raw).split())
    if text.casefold() in _PLACEHOLDERS:
        return None
    if any(p.search(text) for p in _FFMPEG_MESSAGES):
        return None
    return text


def title_from_ffmpeg_line(line: str) -> str | None:
    """StreamTitle carried by one ffmpeg stderr line, if any."""
    m = _UPDATE_RE.search(line) or _DUMP_RE.match(line)
    return clean_title(m.group(1)) if m else None


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed.casefold() if c.isalnum())


def titles_match(a: str | None, b: str | None) -> bool:
    """True when two raw titles name the same song.

    Sources format the same song differently ("Artist - Title", extra
    station tags, diacritics), so the comparison ignores case, accents,
    punctuation and spacing, and accepts one containing the other.
    """
    na, nb = _normalize(a or ""), _normalize(b or "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    return min(len(na), len(nb)) >= 6 and (na in nb or nb in na)
