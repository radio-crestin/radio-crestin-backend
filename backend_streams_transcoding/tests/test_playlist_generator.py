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


class TestParseFFmpegM3u8(unittest.TestCase):
    """Test parsing FFmpeg's live.m3u8."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_m3u8 = playlist_generator.FFMPEG_M3U8
        self.m3u8_path = os.path.join(self.tmpdir, "live.m3u8")
        playlist_generator.FFMPEG_M3U8 = self.m3u8_path

    def tearDown(self):
        playlist_generator.FFMPEG_M3U8 = self._orig_m3u8
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parses_segments(self):
        with open(self.m3u8_path, "w") as f:
            f.write("#EXTM3U\n")
            f.write("#EXT-X-VERSION:3\n")
            f.write("#EXT-X-TARGETDURATION:7\n")
            f.write("#EXT-X-MEDIA-SEQUENCE:100\n")
            f.write("#EXTINF:6.013967,\n")
            f.write("#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:09:11.791+0000\n")
            f.write("100.ts\n")
            f.write("#EXTINF:5.990756,\n")
            f.write("#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:09:17.805+0000\n")
            f.write("101.ts\n")

        segments = playlist_generator.parse_ffmpeg_m3u8()
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0][0], "100.ts")
        self.assertAlmostEqual(segments[0][1], 6.013967, places=5)
        self.assertEqual(segments[0][2], "2026-04-10T10:09:11.791+0000")
        self.assertEqual(segments[1][0], "101.ts")
        self.assertAlmostEqual(segments[1][1], 5.990756, places=5)

    def test_missing_file(self):
        playlist_generator.FFMPEG_M3U8 = "/nonexistent/path.m3u8"
        segments = playlist_generator.parse_ffmpeg_m3u8()
        self.assertEqual(segments, [])


class TestFormatPlaylist(unittest.TestCase):
    """Test HLS playlist formatting."""

    def _make_segments(self, count=3, start_num=100, duration=6.0):
        segments = []
        base_epoch = 1712750000.0
        for i in range(count):
            filename = f"{start_num + i}.ts"
            pdt = playlist_generator._epoch_to_pdt(base_epoch + i * duration)
            segments.append((filename, duration, pdt))
        return segments

    def test_live_playlist_has_no_endlist(self):
        segments = self._make_segments()
        playlist = playlist_generator.format_playlist(segments, is_live=True)
        self.assertNotIn("#EXT-X-ENDLIST", playlist)

    def test_vod_playlist_has_endlist(self):
        segments = self._make_segments()
        playlist = playlist_generator.format_playlist(segments, is_live=False)
        self.assertIn("#EXT-X-ENDLIST", playlist)

    def test_event_playlist_has_type(self):
        segments = self._make_segments()
        playlist = playlist_generator.format_playlist(segments, is_live=False, is_event=True)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", playlist)

    def test_contains_segment_filenames(self):
        segments = self._make_segments(2, start_num=500)
        playlist = playlist_generator.format_playlist(segments)
        self.assertIn("hls/segments/500.ts", playlist)
        self.assertIn("hls/segments/501.ts", playlist)

    def test_contains_program_date_time(self):
        segments = self._make_segments(1)
        playlist = playlist_generator.format_playlist(segments)
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:", playlist)

    def test_media_sequence_uses_segment_number(self):
        segments = self._make_segments(3, start_num=12345)
        playlist = playlist_generator.format_playlist(segments)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:12345", playlist)

    def test_extinf_uses_actual_duration(self):
        segments = [("100.ts", 5.990756, None)]
        playlist = playlist_generator.format_playlist(segments)
        self.assertIn("#EXTINF:5.990756,", playlist)

    def test_target_duration_rounded_up(self):
        segments = [("100.ts", 6.013967, None)]
        playlist = playlist_generator.format_playlist(segments)
        self.assertIn("#EXT-X-TARGETDURATION:7", playlist)

    def test_empty_segments(self):
        playlist = playlist_generator.format_playlist([])
        self.assertIn("#EXT-X-ENDLIST", playlist)
        self.assertIn("#EXTM3U", playlist)


class TestBuildLivePlaylist(unittest.TestCase):
    """Test live playlist window behavior."""

    def _make_segments(self, count):
        segments = []
        base_epoch = 1712750000.0
        for i in range(count):
            filename = f"{1000 + i}.ts"
            pdt = playlist_generator._epoch_to_pdt(base_epoch + i * 6)
            segments.append((filename, 6.0, pdt))
        return segments

    def test_returns_latest_window(self):
        segments = self._make_segments(200)
        playlist = playlist_generator.build_live_playlist(segments)
        # Should contain the last segment
        self.assertIn("hls/segments/1199.ts", playlist)
        # Should NOT contain the first segment
        self.assertNotIn("hls/segments/1000.ts", playlist)

    def test_small_segment_list(self):
        segments = self._make_segments(3)
        playlist = playlist_generator.build_live_playlist(segments)
        self.assertIn("hls/segments/1000.ts", playlist)
        self.assertIn("hls/segments/1002.ts", playlist)

    def test_no_endlist_tag(self):
        segments = self._make_segments(3)
        playlist = playlist_generator.build_live_playlist(segments)
        self.assertNotIn("#EXT-X-ENDLIST", playlist)


class TestBuildHistoricalPlaylist(unittest.TestCase):
    """Test historical/seeking playlist generation."""

    def _make_segments(self, count):
        segments = []
        base_epoch = 1712750000.0
        for i in range(count):
            filename = f"{1000 + i}.ts"
            pdt = playlist_generator._epoch_to_pdt(base_epoch + i * 6)
            segments.append((filename, 6.0, pdt))
        return segments

    def test_event_mode_has_endlist(self):
        segments = self._make_segments(100)
        playlist = playlist_generator.build_historical_playlist(
            segments, 1712750060.0, mode="event"
        )
        self.assertIn("#EXT-X-ENDLIST", playlist)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", playlist)

    def test_near_live_edge_returns_live_playlist(self):
        segments = self._make_segments(100)
        # Request near the end
        target = 1712750000.0 + 95 * 6  # near last segment
        playlist = playlist_generator.build_historical_playlist(segments, target)
        # Should contain the last segment (live behavior)
        self.assertIn("hls/segments/1099.ts", playlist)


class TestGetAllSegments(unittest.TestCase):
    """Test segment discovery combining FFmpeg m3u8 and disk scan."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.segments_dir = os.path.join(self.tmpdir, "segments")
        os.makedirs(self.segments_dir)
        self.m3u8_path = os.path.join(self.tmpdir, "live.m3u8")
        self._orig_m3u8 = playlist_generator.FFMPEG_M3U8
        self._orig_dir = playlist_generator.SEGMENTS_DIR
        playlist_generator.FFMPEG_M3U8 = self.m3u8_path
        playlist_generator.SEGMENTS_DIR = self.segments_dir
        playlist_generator._segments_cache = []
        playlist_generator._segments_cache_time = 0

    def tearDown(self):
        playlist_generator.FFMPEG_M3U8 = self._orig_m3u8
        playlist_generator.SEGMENTS_DIR = self._orig_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_combines_ffmpeg_and_disk(self):
        # Create segment files on disk
        for num in [100, 101, 102, 103]:
            open(os.path.join(self.segments_dir, f"{num}.ts"), "w").close()

        # FFmpeg m3u8 only has recent segments
        with open(self.m3u8_path, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:7\n")
            f.write("#EXT-X-MEDIA-SEQUENCE:102\n")
            f.write("#EXTINF:6.01,\n#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:00:12.000+0000\n102.ts\n")
            f.write("#EXTINF:5.99,\n#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:00:18.000+0000\n103.ts\n")

        segments = playlist_generator.get_all_segments()
        self.assertEqual(len(segments), 4)
        # FFmpeg segments should have accurate durations
        self.assertAlmostEqual(segments[2][1], 6.01, places=2)
        self.assertAlmostEqual(segments[3][1], 5.99, places=2)

    def test_empty_directory(self):
        segments = playlist_generator.get_all_segments()
        self.assertEqual(segments, [])


class TestParsePdt(unittest.TestCase):
    """Test PROGRAM-DATE-TIME parsing."""

    def test_with_timezone_offset(self):
        epoch = playlist_generator._parse_pdt_to_epoch("2026-04-10T10:00:00.000+0000")
        self.assertAlmostEqual(epoch, 1775815200.0, delta=2)

    def test_with_z_suffix(self):
        epoch = playlist_generator._parse_pdt_to_epoch("2026-04-10T10:00:00.000Z")
        self.assertAlmostEqual(epoch, 1775815200.0, delta=2)

    def test_roundtrip(self):
        original = 1712750000.0
        pdt = playlist_generator._epoch_to_pdt(original)
        parsed = playlist_generator._parse_pdt_to_epoch(pdt)
        self.assertAlmostEqual(original, parsed, delta=1)


class TestNoCorsDuplicateHeaders(unittest.TestCase):
    """Verify the playlist generator does NOT set CORS headers (ingress handles it)."""

    def test_send_playlist_no_cors(self):
        handler = playlist_generator.PlaylistHandler.__new__(playlist_generator.PlaylistHandler)
        headers_sent = []

        def mock_send_header(name, value):
            headers_sent.append((name, value))

        def mock_send_response(code):
            pass

        def mock_end_headers():
            pass

        handler.send_header = mock_send_header
        handler.send_response = mock_send_response
        handler.end_headers = mock_end_headers
        handler.wfile = type('MockWfile', (), {'write': lambda self, x: None})()

        handler._send_playlist("#EXTM3U\n")

        header_names = [h[0] for h in headers_sent]
        self.assertNotIn("Access-Control-Allow-Origin", header_names)


if __name__ == "__main__":
    unittest.main()
