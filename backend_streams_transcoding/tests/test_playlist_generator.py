"""
Unit tests for the dynamic HLS playlist generator.
"""

import os
import sys
import tempfile
import time
import unittest

# Add live_streaming scripts to path
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


class TestFindSegmentIndex(unittest.TestCase):
    """Test binary search for segment index."""

    def test_exact_match(self):
        segments = [100, 106, 112, 118, 124]
        self.assertEqual(playlist_generator.find_segment_index(segments, 112), 2)

    def test_between_segments(self):
        segments = [100, 106, 112, 118, 124]
        # Should return index of first segment >= target
        self.assertEqual(playlist_generator.find_segment_index(segments, 110), 2)

    def test_before_first(self):
        segments = [100, 106, 112]
        self.assertEqual(playlist_generator.find_segment_index(segments, 50), 0)

    def test_after_last(self):
        segments = [100, 106, 112]
        self.assertEqual(playlist_generator.find_segment_index(segments, 200), 3)

    def test_empty(self):
        self.assertEqual(playlist_generator.find_segment_index([], 100), 0)


class TestFormatPlaylist(unittest.TestCase):
    """Test HLS playlist formatting."""

    def test_live_playlist_has_no_endlist(self):
        playlist = playlist_generator.format_playlist([100, 106, 112], is_live=True)
        self.assertNotIn("#EXT-X-ENDLIST", playlist)

    def test_vod_playlist_has_endlist(self):
        playlist = playlist_generator.format_playlist([100, 106, 112], is_live=False)
        self.assertIn("#EXT-X-ENDLIST", playlist)

    def test_event_playlist_has_type(self):
        playlist = playlist_generator.format_playlist([100, 106, 112], is_live=False, is_event=True)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", playlist)
        self.assertIn("#EXT-X-ENDLIST", playlist)

    def test_contains_segment_urls(self):
        playlist = playlist_generator.format_playlist([1718000000, 1718000006])
        self.assertIn("hls/segments/1718000000.ts", playlist)
        self.assertIn("hls/segments/1718000006.ts", playlist)

    def test_contains_program_date_time(self):
        playlist = playlist_generator.format_playlist([1718000000])
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:", playlist)

    def test_media_sequence_is_monotonic(self):
        playlist = playlist_generator.format_playlist([100, 106, 112])
        # Sequence = first_ts / segment_duration
        expected_seq = 100 // playlist_generator.SEGMENT_DURATION
        self.assertIn(f"#EXT-X-MEDIA-SEQUENCE:{expected_seq}", playlist)

    def test_target_duration(self):
        playlist = playlist_generator.format_playlist([100])
        self.assertIn(f"#EXT-X-TARGETDURATION:{playlist_generator.SEGMENT_DURATION}", playlist)

    def test_empty_segments(self):
        playlist = playlist_generator.format_playlist([])
        self.assertIn("#EXT-X-ENDLIST", playlist)
        self.assertIn("#EXTM3U", playlist)


class TestBuildLivePlaylist(unittest.TestCase):
    """Test live playlist window behavior."""

    def test_returns_latest_window(self):
        # Create more segments than window size
        segments = list(range(0, 1000, playlist_generator.SEGMENT_DURATION))
        playlist = playlist_generator.build_live_playlist(segments)

        # Should contain the last LIVE_WINDOW_SIZE segments
        last_segment = segments[-1]
        self.assertIn(f"hls/segments/{last_segment}.ts", playlist)

        # Should NOT contain very old segments
        first_segment = segments[0]
        if len(segments) > playlist_generator.LIVE_WINDOW_SIZE:
            self.assertNotIn(f"hls/segments/{first_segment}.ts", playlist)

    def test_small_segment_list(self):
        segments = [100, 106, 112]
        playlist = playlist_generator.build_live_playlist(segments)
        # Should include all segments when fewer than window size
        self.assertIn("hls/segments/100.ts", playlist)
        self.assertIn("hls/segments/112.ts", playlist)

    def test_no_endlist_tag(self):
        segments = [100, 106, 112]
        playlist = playlist_generator.build_live_playlist(segments)
        self.assertNotIn("#EXT-X-ENDLIST", playlist)


class TestBuildHistoricalPlaylist(unittest.TestCase):
    """Test historical/seeking playlist generation."""

    def test_event_mode_has_endlist(self):
        segments = list(range(0, 600, playlist_generator.SEGMENT_DURATION))
        playlist = playlist_generator.build_historical_playlist(segments, 0, mode="event")
        self.assertIn("#EXT-X-ENDLIST", playlist)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", playlist)

    def test_starts_from_requested_timestamp(self):
        segments = list(range(0, 600, playlist_generator.SEGMENT_DURATION))
        target = 120
        playlist = playlist_generator.build_historical_playlist(segments, target)
        # Should contain segment at or near the target
        self.assertIn(f"hls/segments/{target}.ts", playlist)

    def test_near_live_edge_returns_live_playlist(self):
        segments = list(range(0, 600, playlist_generator.SEGMENT_DURATION))
        # Request timestamp near the end
        target = segments[-5]
        playlist = playlist_generator.build_historical_playlist(segments, target)
        # Should contain the latest segment (live behavior)
        self.assertIn(f"hls/segments/{segments[-1]}.ts", playlist)

    def test_event_mode_larger_window(self):
        # Create enough segments
        segments = list(range(0, 3600, playlist_generator.SEGMENT_DURATION))
        playlist = playlist_generator.build_historical_playlist(segments, 0, mode="event")
        # Event mode should include more segments than live window
        segment_count = playlist.count("#EXTINF:")
        self.assertGreater(segment_count, playlist_generator.LIVE_WINDOW_SIZE)


class TestGetAvailableSegments(unittest.TestCase):
    """Test segment discovery from disk."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Override the HLS_DIR for testing
        self._orig_dir = playlist_generator.HLS_DIR
        playlist_generator.HLS_DIR = self.tmpdir
        # Reset cache
        playlist_generator._segments_cache = []
        playlist_generator._segments_cache_time = 0

    def tearDown(self):
        playlist_generator.HLS_DIR = self._orig_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_finds_ts_files(self):
        # Create segment files
        for ts in [1718000000, 1718000006, 1718000012]:
            open(os.path.join(self.tmpdir, f"{ts}.ts"), "w").close()

        segments = playlist_generator.get_available_segments()
        self.assertEqual(segments, [1718000000, 1718000006, 1718000012])

    def test_ignores_non_ts_files(self):
        open(os.path.join(self.tmpdir, "1718000000.ts"), "w").close()
        open(os.path.join(self.tmpdir, "manifest.mpd"), "w").close()
        open(os.path.join(self.tmpdir, "live.m3u8"), "w").close()

        segments = playlist_generator.get_available_segments()
        self.assertEqual(segments, [1718000000])

    def test_sorted_output(self):
        for ts in [1718000012, 1718000000, 1718000006]:
            open(os.path.join(self.tmpdir, f"{ts}.ts"), "w").close()

        segments = playlist_generator.get_available_segments()
        self.assertEqual(segments, [1718000000, 1718000006, 1718000012])

    def test_empty_directory(self):
        segments = playlist_generator.get_available_segments()
        self.assertEqual(segments, [])

    def test_caching(self):
        open(os.path.join(self.tmpdir, "100.ts"), "w").close()
        segments1 = playlist_generator.get_available_segments()

        # Add another file — should still return cached result
        open(os.path.join(self.tmpdir, "106.ts"), "w").close()
        segments2 = playlist_generator.get_available_segments()

        self.assertEqual(segments1, segments2)  # cached, same result


class TestEpochToIso(unittest.TestCase):
    """Test epoch to ISO 8601 conversion."""

    def test_known_timestamp(self):
        # 2024-06-10T00:00:00Z
        result = playlist_generator._epoch_to_iso(1717977600)
        self.assertEqual(result, "2024-06-10T00:00:00.000Z")

    def test_format(self):
        result = playlist_generator._epoch_to_iso(0)
        self.assertRegex(result, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


if __name__ == "__main__":
    unittest.main()
