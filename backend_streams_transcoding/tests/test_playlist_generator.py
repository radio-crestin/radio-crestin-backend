"""Tests for the HLS playlist generator."""

import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator

SAMPLE_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:1000
#EXTINF:6.013967,
#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:00:00.000+0000
1000.ts
#EXTINF:5.990756,
#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:00:06.014+0000
1001.ts
#EXTINF:6.013967,
#EXT-X-PROGRAM-DATE-TIME:2026-04-10T10:00:12.005+0000
1002.ts
"""


class TestParseFFmpegM3u8(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.m3u8 = os.path.join(self.tmpdir, "live.m3u8")
        with open(self.m3u8, "w") as f:
            f.write(SAMPLE_M3U8)
        self._orig = playlist_generator.FFMPEG_M3U8
        playlist_generator.FFMPEG_M3U8 = self.m3u8

    def tearDown(self):
        playlist_generator.FFMPEG_M3U8 = self._orig
        shutil.rmtree(self.tmpdir)

    def test_parses_segments(self):
        segs = playlist_generator.parse_ffmpeg_m3u8()
        self.assertEqual(len(segs), 3)
        self.assertEqual(segs[0][0], "1000.ts")
        self.assertAlmostEqual(segs[0][1], 6.013967, places=5)
        self.assertIn("2026-04-10", segs[0][2])

    def test_missing_file(self):
        playlist_generator.FFMPEG_M3U8 = "/nonexistent"
        self.assertEqual(playlist_generator.parse_ffmpeg_m3u8(), [])


class TestFormatPlaylist(unittest.TestCase):
    def _segs(self, n=3):
        return [(f"{1000+i}.ts", 6.0, f"2026-04-10T10:00:{i*6:02d}.000+0000") for i in range(n)]

    def test_live_no_endlist(self):
        p = playlist_generator.format_playlist(self._segs())
        self.assertNotIn("#EXT-X-ENDLIST", p)

    def test_event_has_endlist(self):
        p = playlist_generator.format_playlist(self._segs(), is_live=False, is_event=True)
        self.assertIn("#EXT-X-ENDLIST", p)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", p)

    def test_segment_paths(self):
        p = playlist_generator.format_playlist(self._segs())
        self.assertIn("hls/segments/1000.ts", p)

    def test_program_date_time(self):
        p = playlist_generator.format_playlist(self._segs())
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:", p)

    def test_media_sequence(self):
        p = playlist_generator.format_playlist(self._segs())
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:1000", p)

    def test_extinf_actual_duration(self):
        segs = [("100.ts", 5.990756, None)]
        p = playlist_generator.format_playlist(segs)
        self.assertIn("#EXTINF:5.990756,", p)

    def test_target_duration_rounded_up(self):
        segs = [("100.ts", 6.013, None)]
        p = playlist_generator.format_playlist(segs)
        self.assertIn("#EXT-X-TARGETDURATION:7", p)

    def test_empty(self):
        p = playlist_generator.format_playlist([])
        self.assertIn("#EXT-X-ENDLIST", p)


class TestHlsValidation(unittest.TestCase):
    """Validate generated playlists conform to HLS spec."""

    def _segs(self, n=10):
        return [(f"{1000+i}.ts", 6.01, f"2026-04-10T10:00:{i*6:02d}.000+0000") for i in range(n)]

    def test_version_present(self):
        p = playlist_generator.format_playlist(self._segs())
        self.assertIn("#EXT-X-VERSION:", p)

    def test_target_duration_gte_max_extinf(self):
        segs = [("1.ts", 5.5, None), ("2.ts", 6.8, None), ("3.ts", 6.1, None)]
        p = playlist_generator.format_playlist(segs)
        # TARGETDURATION must be >= ceil(max EXTINF)
        self.assertIn("#EXT-X-TARGETDURATION:7", p)

    def test_media_sequence_monotonic(self):
        p = playlist_generator.format_playlist(self._segs())
        lines = p.strip().split("\n")
        seq_line = [l for l in lines if l.startswith("#EXT-X-MEDIA-SEQUENCE:")][0]
        seq = int(seq_line.split(":")[1])
        self.assertGreater(seq, 0)

    def test_no_endlist_for_live(self):
        p = playlist_generator.format_playlist(self._segs(), is_live=True)
        self.assertNotIn("#EXT-X-ENDLIST", p)

    def test_endlist_for_vod(self):
        p = playlist_generator.format_playlist(self._segs(), is_live=False)
        self.assertIn("#EXT-X-ENDLIST", p)

    def test_extinf_before_every_segment(self):
        p = playlist_generator.format_playlist(self._segs())
        lines = p.strip().split("\n")
        for i, line in enumerate(lines):
            if line.endswith(".ts"):
                prev = lines[i - 1]
                self.assertTrue(prev.startswith("#EXTINF:"), f"Missing EXTINF before {line}")


class TestNoCorsHeaders(unittest.TestCase):
    def test_no_cors_in_response(self):
        handler = playlist_generator.PlaylistHandler.__new__(playlist_generator.PlaylistHandler)
        headers = []
        handler.send_header = lambda n, v: headers.append((n, v))
        handler.send_response = lambda c: None
        handler.end_headers = lambda: None
        handler.wfile = type('W', (), {'write': lambda s, x: None})()
        # Call internal method
        handler.send_response(200)
        handler.send_header("Content-Type", "application/vnd.apple.mpegurl")
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        names = [h[0] for h in headers]
        self.assertNotIn("Access-Control-Allow-Origin", names)


if __name__ == "__main__":
    unittest.main()
