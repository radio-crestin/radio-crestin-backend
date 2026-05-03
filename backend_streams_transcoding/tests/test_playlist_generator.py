"""Tests for the HLS playlist enhancer.

The enhancer is a thin pass-through: ffmpeg writes the playlist (including
EXT-X-PROGRAM-DATE-TIME via `-hls_flags +program_date_time`); the enhancer
adds EXT-X-DATERANGE song metadata into the header block (per RFC 8216
§4.4.5.1, DATERANGE applies to the entire playlist).

The DATERANGE format is intentionally minimal — see playlist_generator.py
for the full rationale on AVPlayer compatibility (no CLASS, no DURATION,
unique stable IDs).
"""

import os
import re
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


# ── Sample FFmpeg playlist (as ffmpeg writes it: counter-based segments,
# PDT per segment via +program_date_time) ─────────────────────────────

SAMPLE_FFMPEG_PLAYLIST = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:1776250253
#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:00:53.000Z
#EXTINF:5.990744,
seg-1776250253.ts
#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:00:59.000Z
#EXTINF:5.990744,
seg-1776250254.ts
#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:01:05.000Z
#EXTINF:5.990756,
seg-1776250255.ts
#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:01:11.000Z
#EXTINF:6.037189,
seg-1776250256.ts
"""


class TestEpochToPdt(unittest.TestCase):
    def test_format(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.0)
        self.assertIn("T", pdt)
        self.assertTrue(pdt.endswith("Z"))

    def test_milliseconds(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.5)
        self.assertIn(".500Z", pdt)


class TestEnhancePlaylistPassthrough(unittest.TestCase):
    """Without songs, the enhancer must not alter ffmpeg's playlist."""

    def setUp(self):
        # Force empty songs so DATERANGE injection is skipped.
        self._patch = patch.object(playlist_generator, "_get_songs", return_value=[])
        self._patch.start()

    def tearDown(self):
        self._patch.stop()

    def test_preserves_pdt_lines(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:00:53.000Z", enhanced)

    def test_preserves_segments(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        for fn in ("seg-1776250253.ts", "seg-1776250254.ts",
                   "seg-1776250255.ts", "seg-1776250256.ts"):
            self.assertIn(fn, enhanced)

    def test_preserves_extinf(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXTINF:5.990744,", enhanced)
        self.assertIn("#EXTINF:6.037189,", enhanced)

    def test_preserves_media_sequence(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:1776250253", enhanced)

    def test_preserves_version(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-VERSION:3", enhanced)

    def test_no_endlist_for_live(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertNotIn("#EXT-X-ENDLIST", enhanced)

    def test_segment_count_unchanged(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        orig_segs = SAMPLE_FFMPEG_PLAYLIST.count(".ts\n")
        enhanced_segs = sum(1 for l in enhanced.strip().split("\n") if l.endswith(".ts"))
        self.assertEqual(orig_segs, enhanced_segs)


class TestSongDateRangeFormat(unittest.TestCase):
    """Verify the DATERANGE attributes match the AVPlayer-friendly format."""

    def test_basic_attributes(self):
        song = {
            "started_at": 1776167256,
            "title": "Amazing Grace",
            "artist": "Test Artist",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "song_id": 42,
            "station_id": 7,
        }
        result = playlist_generator._daterange_for_song(song)
        self.assertIsNotNone(result)
        self.assertIn("#EXT-X-DATERANGE:", result)
        self.assertIn('START-DATE="', result)
        self.assertIn('X-TITLE="Amazing Grace"', result)
        self.assertIn('X-ARTIST="Test Artist"', result)
        self.assertIn('X-THUMBNAIL-URL="https://example.com/thumb.jpg"', result)
        self.assertIn('X-SONG-ID="42"', result)
        self.assertIn('X-STATION-ID="7"', result)

    def test_no_class_attribute(self):
        """CLASS triggers AVPlayer interstitial / ad behavior — must be absent."""
        song = {"started_at": 1776167256, "title": "X", "artist": "Y"}
        result = playlist_generator._daterange_for_song(song)
        self.assertNotIn("CLASS=", result)

    def test_no_duration_attribute(self):
        """DURATION makes AVPlayer treat the range as a hard end — must be absent."""
        song = {
            "started_at": 1776167256,
            "title": "X",
            "artist": "Y",
            "duration_seconds": 240,
        }
        result = playlist_generator._daterange_for_song(song)
        self.assertNotIn("DURATION=", result)

    def test_unique_id_uses_backend_song_id_when_present(self):
        song = {"started_at": 1776167256, "title": "X", "artist": "Y", "song_id": 42}
        result = playlist_generator._daterange_for_song(song)
        # ID must include song_id so the same backend song at different
        # times gets different DATERANGE IDs across plays.
        self.assertIn(f'ID="song-42-{1776167256}"', result)

    def test_unique_id_falls_back_to_started_at(self):
        song = {"started_at": 1776167256, "title": "X", "artist": "Y"}
        result = playlist_generator._daterange_for_song(song)
        self.assertIn(f'ID="song-{1776167256}"', result)

    def test_id_never_uses_slot_index(self):
        """Slot-style IDs ('song-0', 'song-1') trip AVPlayer's
        same-ID-different-attributes detection — we must always use a
        per-occurrence value."""
        song = {"started_at": 1776167256, "title": "X", "artist": "Y"}
        result = playlist_generator._daterange_for_song(song)
        m = re.search(r'ID="([^"]+)"', result)
        self.assertIsNotNone(m)
        # The ID must contain the occurrence epoch, not just a slot index.
        self.assertIn(str(int(song["started_at"])), m.group(1))

    def test_start_date_has_milliseconds(self):
        song = {"started_at": 1776167256.5, "title": "X", "artist": "Y"}
        result = playlist_generator._daterange_for_song(song)
        m = re.search(r'START-DATE="([^"]+)"', result)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"\.\d{3}Z$")

    def test_quotes_in_title_are_escaped(self):
        song = {
            "started_at": 1776167256,
            "title": 'He said "hello"',
            "artist": "Y",
        }
        result = playlist_generator._daterange_for_song(song)
        # Single-character replacement: " → '
        self.assertNotIn('"hello"', result.split("X-TITLE=")[1].split(",")[0])

    def test_returns_none_without_started_at(self):
        song = {"title": "X", "artist": "Y"}
        result = playlist_generator._daterange_for_song(song)
        self.assertIsNone(result)

    def test_returns_none_without_title_and_artist(self):
        song = {"started_at": 1776167256}
        result = playlist_generator._daterange_for_song(song)
        self.assertIsNone(result)


class TestDaterangeInjection(unittest.TestCase):
    """DATERANGE tags must be in the playlist header, not adjacent to a
    specific segment — that's what AVPlayer expects per RFC 8216 §4.4.5.1."""

    def test_daterange_inserted_in_header(self):
        # Use a recent epoch so the song falls inside the live window.
        song = {
            "started_at": time.time() - 60,
            "title": "Song A",
            "artist": "Artist",
            "song_id": 1,
        }
        with patch.object(playlist_generator, "_get_songs", return_value=[song]):
            enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        idx_daterange = next(i for i, l in enumerate(lines) if l.startswith("#EXT-X-DATERANGE:"))
        idx_first_pdt = next(i for i, l in enumerate(lines) if l.startswith("#EXT-X-PROGRAM-DATE-TIME"))
        idx_first_segment = next(i for i, l in enumerate(lines) if l.endswith(".ts"))
        # DATERANGE must come before the first PDT/segment.
        self.assertLess(idx_daterange, idx_first_pdt)
        self.assertLess(idx_daterange, idx_first_segment)

    def test_old_songs_are_filtered_out(self):
        # Song from 1+ year ago — must not appear.
        song = {
            "started_at": time.time() - 365 * 86400,
            "title": "Ancient",
            "artist": "X",
        }
        with patch.object(playlist_generator, "_get_songs", return_value=[song]):
            enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertNotIn("Ancient", enhanced)

    def test_duplicate_ids_dedup(self):
        song = {
            "started_at": time.time() - 30,
            "title": "Same",
            "artist": "X",
            "song_id": 5,
        }
        with patch.object(playlist_generator, "_get_songs", return_value=[song, song]):
            enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertEqual(enhanced.count("#EXT-X-DATERANGE:"), 1)


if __name__ == "__main__":
    unittest.main()
