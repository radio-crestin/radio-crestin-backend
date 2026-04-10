"""
Unit tests for the unified DASH+HLS playlist generator.
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


SAMPLE_MPD = """<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" availabilityStartTime="2026-04-10T10:00:00.000Z"
     type="dynamic" minBufferTime="PT6S">
  <Period id="0" start="PT0S">
    <AdaptationSet id="0" contentType="audio" mimeType="audio/mp4">
      <Representation id="0" bandwidth="32000">
        <SegmentTemplate timescale="48000" initialization="segments/init-0.m4s"
                         media="segments/chunk-0-$Number%09d$.m4s" startNumber="1">
          <SegmentTimeline>
            <S t="0" d="288000" r="9" />
          </SegmentTimeline>
        </SegmentTemplate>
      </Representation>
    </AdaptationSet>
    <AdaptationSet id="1" contentType="audio" mimeType="audio/mp4">
      <Representation id="1" bandwidth="96000">
        <SegmentTemplate timescale="48000" initialization="segments/init-1.m4s"
                         media="segments/chunk-1-$Number%09d$.m4s" startNumber="1">
          <SegmentTimeline>
            <S t="0" d="288000" r="9" />
          </SegmentTimeline>
        </SegmentTemplate>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""


class TestDashManifestParser(unittest.TestCase):
    """Test DASH MPD parsing."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mpd_path = os.path.join(self.tmpdir, "manifest.mpd")
        with open(self.mpd_path, "w") as f:
            f.write(SAMPLE_MPD)
        self._orig = playlist_generator.DASH_MANIFEST
        playlist_generator.DASH_MANIFEST = self.mpd_path
        playlist_generator._manifest_cache = None

    def tearDown(self):
        playlist_generator.DASH_MANIFEST = self._orig
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_parses_two_representations(self):
        m = playlist_generator.DashManifest.parse(self.mpd_path)
        self.assertEqual(len(m.representations), 2)
        self.assertIn("0", m.representations)
        self.assertIn("1", m.representations)

    def test_bandwidth(self):
        m = playlist_generator.DashManifest.parse(self.mpd_path)
        self.assertEqual(m.representations["0"]["bandwidth"], 32000)
        self.assertEqual(m.representations["1"]["bandwidth"], 96000)

    def test_init_segment(self):
        m = playlist_generator.DashManifest.parse(self.mpd_path)
        self.assertEqual(m.representations["0"]["init_seg"], "segments/init-0.m4s")
        self.assertEqual(m.representations["1"]["init_seg"], "segments/init-1.m4s")

    def test_segments_count(self):
        m = playlist_generator.DashManifest.parse(self.mpd_path)
        # r="9" means 10 repetitions (r+1)
        self.assertEqual(len(m.representations["0"]["segments"]), 10)

    def test_segment_duration(self):
        m = playlist_generator.DashManifest.parse(self.mpd_path)
        seg = m.representations["0"]["segments"][0]
        # d=288000, timescale=48000 → 6 seconds
        self.assertAlmostEqual(seg[1], 6.0, places=1)

    def test_missing_file(self):
        m = playlist_generator.DashManifest.parse("/nonexistent.mpd")
        self.assertEqual(len(m.representations), 0)


class TestSegmentFilename(unittest.TestCase):
    """Test DASH media template resolution."""

    def test_number_format(self):
        result = playlist_generator._segment_filename(
            "segments/chunk-$RepresentationID$-$Number%09d$.m4s", "0", 42
        )
        self.assertEqual(result, "segments/chunk-0-000000042.m4s")

    def test_simple_number(self):
        result = playlist_generator._segment_filename(
            "segments/chunk-$RepresentationID$-$Number$.m4s", "1", 5
        )
        self.assertEqual(result, "segments/chunk-1-5.m4s")


class TestHlsVariant(unittest.TestCase):
    """Test HLS variant playlist generation from DASH data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mpd_path = os.path.join(self.tmpdir, "manifest.mpd")
        with open(self.mpd_path, "w") as f:
            f.write(SAMPLE_MPD)
        self._orig = playlist_generator.DASH_MANIFEST
        playlist_generator.DASH_MANIFEST = self.mpd_path
        playlist_generator._manifest_cache = None

    def tearDown(self):
        playlist_generator.DASH_MANIFEST = self._orig
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_live_playlist_no_endlist(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertNotIn("#EXT-X-ENDLIST", playlist)

    def test_event_playlist_has_endlist(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0", is_live=False, is_event=True)
        self.assertIn("#EXT-X-ENDLIST", playlist)
        self.assertIn("#EXT-X-PLAYLIST-TYPE:EVENT", playlist)

    def test_has_ext_x_map(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertIn('#EXT-X-MAP:URI="segments/segments/init-0.m4s"', playlist)

    def test_version_7(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertIn("#EXT-X-VERSION:7", playlist)

    def test_segment_references(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertIn("segments/segments/chunk-0-000000001.m4s", playlist)

    def test_has_program_date_time(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:", playlist)

    def test_extinf_uses_actual_duration(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_variant(m, "0")
        self.assertIn("#EXTINF:6.000000,", playlist)


class TestHlsMaster(unittest.TestCase):
    """Test HLS master playlist."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mpd_path = os.path.join(self.tmpdir, "manifest.mpd")
        with open(self.mpd_path, "w") as f:
            f.write(SAMPLE_MPD)
        self._orig = playlist_generator.DASH_MANIFEST
        playlist_generator.DASH_MANIFEST = self.mpd_path
        playlist_generator._manifest_cache = None

    def tearDown(self):
        playlist_generator.DASH_MANIFEST = self._orig
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_has_two_variants(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_master(m)
        self.assertIn("hls/low.m3u8", playlist)
        self.assertIn("hls/high.m3u8", playlist)

    def test_has_bandwidth(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_master(m)
        self.assertIn("BANDWIDTH=32000", playlist)
        self.assertIn("BANDWIDTH=96000", playlist)

    def test_has_opus_codec(self):
        m = playlist_generator.get_manifest()
        playlist = playlist_generator.build_hls_master(m)
        self.assertIn('CODECS="opus"', playlist)


class TestNoCorsDuplicateHeaders(unittest.TestCase):
    """Verify playlist generator does NOT set CORS headers."""

    def test_send_m3u8_no_cors(self):
        handler = playlist_generator.PlaylistHandler.__new__(playlist_generator.PlaylistHandler)
        headers_sent = []
        handler.send_header = lambda name, value: headers_sent.append((name, value))
        handler.send_response = lambda code: None
        handler.end_headers = lambda: None
        handler.wfile = type('W', (), {'write': lambda self, x: None})()

        handler._send_m3u8("#EXTM3U\n")
        header_names = [h[0] for h in headers_sent]
        self.assertNotIn("Access-Control-Allow-Origin", header_names)


if __name__ == "__main__":
    unittest.main()
