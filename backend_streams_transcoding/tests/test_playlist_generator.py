"""Tests for the HLS playlist generator (pure math, clock-aligned segments)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


class TestSnap(unittest.TestCase):
    def test_exact_boundary(self):
        self.assertEqual(playlist_generator.snap(1776167256), 1776167256)

    def test_between_boundaries(self):
        self.assertEqual(playlist_generator.snap(1776167259), 1776167256)

    def test_one_before_boundary(self):
        self.assertEqual(playlist_generator.snap(1776167261), 1776167256)

    def test_float_epoch(self):
        self.assertEqual(playlist_generator.snap(1776167259.5), 1776167256)


class TestGeneratePlaylist(unittest.TestCase):
    def test_basic_structure(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 3)
        self.assertIn("#EXTM3U", p)
        self.assertIn("#EXT-X-VERSION:9", p)
        self.assertIn("#EXT-X-TARGETDURATION:7", p)
        self.assertIn("#EXT-X-INDEPENDENT-SEGMENTS", p)

    def test_correct_segment_names(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 3)
        self.assertIn("segments/1776167256.ts", p)
        self.assertIn("segments/1776167262.ts", p)
        self.assertIn("segments/1776167268.ts", p)

    def test_correct_segment_count(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 5)
        count = p.count("#EXTINF:")
        self.assertEqual(count, 5)

    def test_program_date_time(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 1)
        self.assertIn("#EXT-X-PROGRAM-DATE-TIME:", p)

    def test_no_endlist_for_live(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 3)
        self.assertNotIn("#EXT-X-ENDLIST", p)

    def test_no_ll_hls_directives(self):
        """No blocking reload, no server control."""
        p = playlist_generator.generate_playlist("aac", 1776167256, 3)
        self.assertNotIn("CAN-BLOCK-RELOAD", p)
        self.assertNotIn("EXT-X-SERVER-CONTROL", p)
        self.assertNotIn("EXT-X-SKIP", p)

    def test_media_sequence_deterministic(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 3)
        seq = 1776167256 // 6
        self.assertIn(f"#EXT-X-MEDIA-SEQUENCE:{seq}", p)

    def test_extinf_before_every_segment(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 10)
        lines = p.strip().split("\n")
        for i, line in enumerate(lines):
            if line.endswith(".ts"):
                prev = lines[i - 1]
                self.assertTrue(prev.startswith("#EXTINF:"), f"Missing EXTINF before {line}")

    def test_segments_are_spaced_by_duration(self):
        p = playlist_generator.generate_playlist("aac", 1776167256, 5)
        lines = p.strip().split("\n")
        seg_lines = [l for l in lines if l.endswith(".ts")]
        epochs = [int(l.replace("segments/", "").replace(".ts", "")) for l in seg_lines]
        for i in range(1, len(epochs)):
            self.assertEqual(epochs[i] - epochs[i - 1], 6)


class TestLiveRedirect(unittest.TestCase):
    def test_returns_aligned_timestamp(self):
        ts = playlist_generator.live_redirect_timestamp()
        self.assertEqual(ts % playlist_generator.SEGMENT_DURATION, 0)

    def test_deterministic_within_round_window(self):
        """Same result within LIVE_REDIRECT_ROUND window."""
        ts1 = playlist_generator.live_redirect_timestamp()
        ts2 = playlist_generator.live_redirect_timestamp()
        self.assertEqual(ts1, ts2)


class TestEpochToPdt(unittest.TestCase):
    def test_format(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.0)
        self.assertIn("T", pdt)
        self.assertTrue(pdt.endswith("Z"))

    def test_milliseconds(self):
        pdt = playlist_generator._epoch_to_pdt(1776167256.5)
        self.assertIn(".500Z", pdt)


if __name__ == "__main__":
    unittest.main()
