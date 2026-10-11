"""Rejects text that is not a song title or artist.

The streaming pods parse ICY titles out of ffmpeg's log output; a decoder
message that continued a StreamTitle line ("ChannelElement 3.1 missing") was
stored as alt-fm's song on 2026-09-02. The pods now filter these too
(live_streaming/scripts/song_titles.py); this is the server-side guard.
"""

import re
from typing import Optional

_FFMPEG_MESSAGES = (
    re.compile(r"^\[[\w:.-]+ @ (0x)?[0-9a-fA-F]+\]"),
    re.compile(r"\bChannelElement \d+\.\d+ missing\b", re.IGNORECASE),
    re.compile(r"\bchannel element \d+\.\d+ (is not allocated|duplicate)\b",
               re.IGNORECASE),
    re.compile(r"\b(Error while decoding|Invalid data found when processing "
               r"input)\b", re.IGNORECASE),
)
_PLACEHOLDERS = {"", "-", "--", "n/a", "na", "null", "none", "undefined"}


def is_garbage_song_text(value: Optional[str]) -> bool:
    """True for ffmpeg log messages and empty placeholders."""
    text = " ".join(str(value or "").split())
    return text.casefold() in _PLACEHOLDERS or any(p.search(text) for p in _FFMPEG_MESSAGES)


def clean_song_text(value: Optional[str]) -> Optional[str]:
    """`value` with whitespace collapsed, or None when it is not song text."""
    if value is None or is_garbage_song_text(value):
        return None
    return " ".join(str(value).split())
