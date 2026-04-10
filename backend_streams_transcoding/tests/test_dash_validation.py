"""
DASH manifest validation tests.

Validates that DASH manifests conform to the spec:
- No gaps in segment timeline
- Proper timing attributes
- Buffer hints present
"""

import os
import sys
import tempfile
import shutil
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import dash_patcher

SAMPLE_MPD = """<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"
     availabilityStartTime="2026-04-10T10:00:00.000Z"
     type="dynamic"
     minBufferTime="PT2S"
     publishTime="2026-04-10T10:05:00.000Z">
  <Period id="0" start="PT0S">
    <AdaptationSet id="0" contentType="audio" mimeType="audio/mp4">
      <Representation id="0" bandwidth="32000" codecs="opus">
        <SegmentTemplate timescale="48000"
                         initialization="0/init.m4s"
                         media="0/chunk-$Number%09d$.m4s"
                         startNumber="1">
          <SegmentTimeline>
            <S t="0" d="288000" />
            <S d="288000" />
            <S d="288000" />
            <S d="288000" />
            <S d="288000" />
          </SegmentTimeline>
        </SegmentTemplate>
      </Representation>
    </AdaptationSet>
    <AdaptationSet id="1" contentType="audio" mimeType="audio/mp4">
      <Representation id="1" bandwidth="96000" codecs="opus">
        <SegmentTemplate timescale="48000"
                         initialization="1/init.m4s"
                         media="1/chunk-$Number%09d$.m4s"
                         startNumber="1">
          <SegmentTimeline>
            <S t="0" d="288000" />
            <S d="288000" />
            <S d="288000" />
            <S d="288000" />
            <S d="288000" />
          </SegmentTimeline>
        </SegmentTemplate>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""


class TestDashTimelineNoGaps(unittest.TestCase):
    """Validate DASH segment timeline has no gaps."""

    def _parse_timeline(self, mpd_str: str) -> list[list[tuple]]:
        """Parse all segment timelines into list of (t, d) tuples per AdaptationSet."""
        root = ET.fromstring(mpd_str)
        ns = ""
        m = __import__("re").match(r"\{(.+)\}", root.tag)
        if m:
            ns = m.group(1)

        def tag(name):
            return f"{{{ns}}}{name}" if ns else name

        timelines = []
        for adapt in root.iter(tag("AdaptationSet")):
            for rep in adapt.iter(tag("Representation")):
                seg_tmpl = rep.find(tag("SegmentTemplate"))
                if seg_tmpl is None:
                    seg_tmpl = adapt.find(tag("SegmentTemplate"))
                if seg_tmpl is None:
                    continue
                timescale = int(seg_tmpl.get("timescale", "1"))
                tl = seg_tmpl.find(tag("SegmentTimeline"))
                if tl is None:
                    continue

                segments = []
                current_t = 0
                for s in tl.iter(tag("S")):
                    t = int(s.get("t", str(current_t)))
                    d = int(s.get("d", "0"))
                    r = int(s.get("r", "0"))
                    current_t = t
                    for _ in range(r + 1):
                        segments.append((current_t / timescale, d / timescale))
                        current_t += d
                timelines.append(segments)

        return timelines

    def test_no_gaps_in_timeline(self):
        timelines = self._parse_timeline(SAMPLE_MPD)
        self.assertGreater(len(timelines), 0)
        for segments in timelines:
            for i in range(1, len(segments)):
                prev_end = segments[i - 1][0] + segments[i - 1][1]
                curr_start = segments[i][0]
                gap = abs(curr_start - prev_end)
                self.assertLess(gap, 0.001,
                                f"Gap of {gap}s between segment {i-1} and {i}")

    def test_consistent_segment_duration(self):
        timelines = self._parse_timeline(SAMPLE_MPD)
        for segments in timelines:
            durations = [s[1] for s in segments]
            if durations:
                avg = sum(durations) / len(durations)
                for d in durations:
                    # Duration should not vary more than 20% from average
                    self.assertAlmostEqual(d, avg, delta=avg * 0.2,
                                          msg=f"Duration {d} deviates from avg {avg}")

    def test_both_representations_same_segment_count(self):
        timelines = self._parse_timeline(SAMPLE_MPD)
        if len(timelines) >= 2:
            self.assertEqual(len(timelines[0]), len(timelines[1]),
                             "Both Opus qualities should have same segment count")


class TestDashPatcher(unittest.TestCase):
    """Test DASH manifest patching."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mpd = os.path.join(self.tmpdir, "manifest.mpd")
        self._orig = dash_patcher.MANIFEST
        dash_patcher.MANIFEST = self.mpd
        dash_patcher._last_mtime = 0.0

    def tearDown(self):
        dash_patcher.MANIFEST = self._orig
        shutil.rmtree(self.tmpdir)

    def test_adds_suggested_presentation_delay(self):
        with open(self.mpd, "w") as f:
            f.write(SAMPLE_MPD)
        dash_patcher.patch_manifest()
        with open(self.mpd) as f:
            content = f.read()
        self.assertIn("suggestedPresentationDelay", content)
        self.assertIn(f"PT{dash_patcher.BUFFER_SECONDS}S", content)

    def test_fixes_small_min_buffer_time(self):
        with open(self.mpd, "w") as f:
            f.write(SAMPLE_MPD)  # has minBufferTime="PT2S"
        dash_patcher.patch_manifest()
        with open(self.mpd) as f:
            content = f.read()
        self.assertIn(f'minBufferTime="PT{dash_patcher.MIN_BUFFER}S"', content)

    def test_fixes_webm_mime_type(self):
        mpd_with_webm = SAMPLE_MPD.replace('mimeType="audio/mp4"', 'mimeType="audio/webm"')
        with open(self.mpd, "w") as f:
            f.write(mpd_with_webm)
        dash_patcher.patch_manifest()
        with open(self.mpd) as f:
            content = f.read()
        self.assertNotIn('audio/webm', content)
        self.assertIn('audio/mp4', content)

    def test_overrides_existing_presentation_delay(self):
        mpd_with_delay = SAMPLE_MPD.replace('type="dynamic"',
            'type="dynamic" suggestedPresentationDelay="PT6S"')
        with open(self.mpd, "w") as f:
            f.write(mpd_with_delay)
        dash_patcher.patch_manifest()
        with open(self.mpd) as f:
            content = f.read()
        self.assertIn(f'suggestedPresentationDelay="PT{dash_patcher.BUFFER_SECONDS}S"', content)
        self.assertNotIn('suggestedPresentationDelay="PT6S"', content)

    def test_skips_if_not_modified(self):
        with open(self.mpd, "w") as f:
            f.write(SAMPLE_MPD)
        dash_patcher.patch_manifest()
        # Read patched content
        with open(self.mpd) as f:
            first = f.read()
        # Patch again (should skip, same mtime)
        dash_patcher.patch_manifest()
        with open(self.mpd) as f:
            second = f.read()
        self.assertEqual(first, second)

    def test_missing_file_no_crash(self):
        dash_patcher.MANIFEST = "/nonexistent/manifest.mpd"
        dash_patcher.patch_manifest()  # Should not raise


class TestDashManifestStructure(unittest.TestCase):
    """Validate DASH manifest has required attributes."""

    def test_has_availability_start_time(self):
        root = ET.fromstring(SAMPLE_MPD)
        self.assertIsNotNone(root.get("availabilityStartTime"))

    def test_is_dynamic(self):
        root = ET.fromstring(SAMPLE_MPD)
        self.assertEqual(root.get("type"), "dynamic")

    def test_has_min_buffer_time(self):
        root = ET.fromstring(SAMPLE_MPD)
        self.assertIsNotNone(root.get("minBufferTime"))

    def test_has_adaptation_sets(self):
        root = ET.fromstring(SAMPLE_MPD)
        ns = ""
        m = __import__("re").match(r"\{(.+)\}", root.tag)
        if m:
            ns = m.group(1)
        adapt_sets = list(root.iter(f"{{{ns}}}AdaptationSet" if ns else "AdaptationSet"))
        self.assertGreaterEqual(len(adapt_sets), 1, "Should have at least 1 AdaptationSet")

    def test_representations_have_bandwidth(self):
        root = ET.fromstring(SAMPLE_MPD)
        ns = ""
        m = __import__("re").match(r"\{(.+)\}", root.tag)
        if m:
            ns = m.group(1)
        for rep in root.iter(f"{{{ns}}}Representation" if ns else "Representation"):
            bw = rep.get("bandwidth")
            self.assertIsNotNone(bw)
            self.assertGreater(int(bw), 0)


if __name__ == "__main__":
    unittest.main()
