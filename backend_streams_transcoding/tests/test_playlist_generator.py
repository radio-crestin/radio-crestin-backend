"""Tests for the HLS playlist enhancer.

The enhancer is a thin pass-through: ffmpeg writes the playlist (including
EXT-X-PROGRAM-DATE-TIME via `-hls_flags +program_date_time`); the enhancer
adds EXT-X-DATERANGE song metadata before any segment whose epoch-based
filename matches a song's started_at timestamp.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


# ── Sample FFmpeg playlist (as ffmpeg writes it: includes PDT) ────────

SAMPLE_FFMPEG_PLAYLIST = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:393
#EXT-X-PROGRAM-DATE-TIME:2026-04-15T12:00:53.000Z
#EXTINF:5.990744,
1776250253.ts
#EXTINF:5.990744,
1776250259.ts
#EXTINF:5.990756,
1776250265.ts
#EXTINF:6.037189,
1776250271.ts
"""


class TestEpochToPdt(unittest.TestCase):
    def test_format(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.0)
        self.assertIn("T", pdt)
        self.assertTrue(pdt.endswith("Z"))

    def test_milliseconds(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.5)
        self.assertIn(".500Z", pdt)


class TestExtractEpoch(unittest.TestCase):
    def test_bare_filename(self):
        self.assertEqual(playlist_generator._extract_epoch("1776250253.ts"), 1776250253)

    def test_with_path_prefix(self):
        self.assertEqual(playlist_generator._extract_epoch("segments/1776250253.ts"), 1776250253)

    def test_no_match(self):
        self.assertIsNone(playlist_generator._extract_epoch("#EXTINF:6.000,"))

    def test_short_number(self):
        """Numbers shorter than 10 digits shouldn't match (not epoch)."""
        self.assertIsNone(playlist_generator._extract_epoch("12345.ts"))


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
        for fn in ("1776250253.ts", "1776250259.ts", "1776250265.ts", "1776250271.ts"):
            self.assertIn(fn, enhanced)

    def test_preserves_extinf(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXTINF:5.990744,", enhanced)
        self.assertIn("#EXTINF:6.037189,", enhanced)

    def test_preserves_media_sequence(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:393", enhanced)

    def test_preserves_version(self):
        """Enhancer must not alter EXT-X-VERSION (ffmpeg sets it appropriately)."""
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


class TestSongDateRangeEmbedding(unittest.TestCase):
    """Verify EXT-X-DATERANGE song metadata injection when songs are present."""

    def test_daterange_for_song(self):
        song = {
            "started_at": 1776167256,
            "started_at_iso": "2026-04-15T12:00:56.000Z",
            "title": "Amazing Grace",
            "artist": "Test Artist",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "song_id": 42,
            "station_id": 7,
            "duration_seconds": 240,
        }
        result = playlist_generator._daterange_for_song(song, 0)
        self.assertIn('EXT-X-DATERANGE:ID="song-0"', result)
        self.assertIn('START-DATE="2026-04-15T12:00:56.000Z"', result)
        self.assertIn('CLASS="com.radiocrestin.song"', result)
        self.assertIn('X-TITLE="Amazing Grace"', result)
        self.assertIn('X-ARTIST="Test Artist"', result)
        self.assertIn('X-THUMBNAIL-URL="https://example.com/thumb.jpg"', result)
        self.assertIn('X-SONG-ID="42"', result)
        self.assertIn('X-STATION-ID="7"', result)
        self.assertIn("DURATION=240", result)

    def test_daterange_escapes_quotes_in_title(self):
        song = {
            "started_at": 1776167256,
            "title": 'He said "hello"',
            "artist": "",
        }
        result = playlist_generator._daterange_for_song(song, 0)
        self.assertNotIn('"hello"', result.split("X-TITLE=")[1].split(",")[0])

    def test_daterange_without_optional_fields(self):
        song = {
            "started_at": 1776167256,
            "title": "Simple Song",
            "artist": "Artist",
        }
        result = playlist_generator._daterange_for_song(song, 0)
        self.assertIn("X-TITLE=", result)
        self.assertNotIn("X-THUMBNAIL-URL", result)
        self.assertNotIn("X-SONG-ID", result)
        self.assertNotIn("DURATION=", result)

    def test_daterange_inserted_before_matching_segment(self):
        """A song whose started_at falls inside segment X's window must produce a
        DATERANGE line that appears immediately before that segment's filename."""
        # Segment 1776250259.ts spans wallclock [1776250259, 1776250265).
        song = {
            "started_at": 1776250261,  # inside segment 2's window
            "title": "Song A",
            "artist": "Artist",
        }
        with patch.object(playlist_generator, "_get_songs", return_value=[song]):
            enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        idx_daterange = next(i for i, l in enumerate(lines) if l.startswith("#EXT-X-DATERANGE:"))
        idx_segment = next(i for i, l in enumerate(lines) if l == "1776250259.ts")
        self.assertLess(idx_daterange, idx_segment, "DATERANGE must appear before its segment")
        # And it must be adjacent (no other segment between them).
        between = [l for l in lines[idx_daterange + 1: idx_segment] if l.endswith(".ts")]
        self.assertEqual(between, [])


if __name__ == "__main__":
    unittest.main()
