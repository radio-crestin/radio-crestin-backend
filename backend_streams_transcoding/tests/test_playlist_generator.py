"""Tests for the HLS playlist enhancer (reads FFmpeg playlist, adds PDT + song metadata)."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts"
))

import playlist_generator


# ── Sample FFmpeg playlist (what FFmpeg actually writes to live.m3u8) ─

SAMPLE_FFMPEG_PLAYLIST = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:393
#EXTINF:5.990744,
1776250253.ts
#EXTINF:5.990744,
1776250259.ts
#EXTINF:5.990756,
1776250265.ts
#EXTINF:6.037189,
1776250271.ts
"""

SAMPLE_3_SEGMENTS = """\
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:6.000000,
1776254400.ts
#EXTINF:6.000000,
1776254406.ts
#EXTINF:6.000000,
1776254412.ts
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


class TestEnhancePlaylist(unittest.TestCase):
    def test_adds_program_date_time_for_every_segment(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        seg_count = sum(1 for l in lines if l.endswith(".ts"))
        pdt_count = sum(1 for l in lines if l.startswith("#EXT-X-PROGRAM-DATE-TIME:"))
        self.assertEqual(seg_count, 4)
        self.assertEqual(pdt_count, seg_count)

    def test_pdt_appears_before_segment(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        for i, line in enumerate(lines):
            if line.endswith(".ts"):
                # Look backwards for PDT
                found = False
                for j in range(i - 1, max(i - 3, -1), -1):
                    if lines[j].startswith("#EXT-X-PROGRAM-DATE-TIME:"):
                        found = True
                        break
                self.assertTrue(found, f"Missing PDT before {line}")

    def test_first_pdt_matches_first_segment_epoch(self):
        """The anchor PDT equals the first segment's filename epoch."""
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        first_pdt = next(l for l in lines if l.startswith("#EXT-X-PROGRAM-DATE-TIME:"))
        self.assertEqual(
            first_pdt,
            f"#EXT-X-PROGRAM-DATE-TIME:{playlist_generator._epoch_to_pdt(1776250253)}",
        )

    def test_pdt_deltas_equal_extinf(self):
        """PDT delta between consecutive segments must equal the prior segment's EXTINF.

        This is the invariant that prevents hls.js stalls ("Stuck — no fragment loaded"):
        if wallclock-derived filenames drift relative to media durations, the cumulative
        PDT still stays consistent with what the player expects.
        """
        import datetime as _dt
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        lines = enhanced.strip().split("\n")
        pdts: list[float] = []
        extinfs: list[float] = []
        for line in lines:
            if line.startswith("#EXTINF:"):
                extinfs.append(playlist_generator._parse_extinf(line))
            elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
                ts = line[len("#EXT-X-PROGRAM-DATE-TIME:"):]
                pdts.append(_dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                            .replace(tzinfo=_dt.timezone.utc).timestamp())
        self.assertEqual(len(pdts), 4)
        for i in range(1, len(pdts)):
            self.assertAlmostEqual(pdts[i] - pdts[i - 1], extinfs[i - 1], places=2)

    def test_pdt_is_iso8601_utc(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_3_SEGMENTS)
        pdt_pattern = re.compile(
            r"#EXT-X-PROGRAM-DATE-TIME:"
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z"
        )
        pdt_lines = [l for l in enhanced.strip().split("\n")
                     if l.startswith("#EXT-X-PROGRAM-DATE-TIME:")]
        self.assertGreater(len(pdt_lines), 0)
        for pdt_line in pdt_lines:
            self.assertRegex(pdt_line, pdt_pattern)

    def test_preserves_original_segments(self):
        """The original segment filenames must be preserved exactly."""
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("1776250253.ts", enhanced)
        self.assertIn("1776250259.ts", enhanced)
        self.assertIn("1776250265.ts", enhanced)
        self.assertIn("1776250271.ts", enhanced)

    def test_preserves_extinf(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXTINF:5.990744,", enhanced)
        self.assertIn("#EXTINF:6.037189,", enhanced)

    def test_preserves_media_sequence(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:393", enhanced)

    def test_upgrades_version_to_9(self):
        enhanced = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertIn("#EXT-X-VERSION:9", enhanced)
        self.assertNotIn("#EXT-X-VERSION:3", enhanced)

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


def _extract_pdts(enhanced: str) -> dict[str, str]:
    """Parse enhanced playlist into {segment_filename: pdt_string} for stability checks."""
    out: dict[str, str] = {}
    pending_pdt: str | None = None
    for line in enhanced.strip().split("\n"):
        if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            pending_pdt = line[len("#EXT-X-PROGRAM-DATE-TIME:"):]
        elif line.endswith(".ts") and pending_pdt is not None:
            out[line.strip()] = pending_pdt
            pending_pdt = None
    return out


class TestPdtStabilityAcrossSlides(unittest.TestCase):
    """Regression: same segment file MUST produce the same PDT on every playlist
    refresh, including after the sliding window advances. The pre-fix version
    re-anchored on the new first segment each call, drifting overlapping
    segments' PDTs by ~10–14ms per slide. iOS AVPlayer interprets that drift
    as a moving live-edge target and seeks forward to "catch up" — audible
    as the stream "jumping to different sections".
    """

    def setUp(self):
        # Sidecars persist between calls — give each test a fresh dir.
        self._tmpdir = tempfile.mkdtemp(prefix="pdt_test_")
        self._original_segment_dir = playlist_generator.SEGMENT_DIR
        playlist_generator.SEGMENT_DIR = self._tmpdir

    def tearDown(self):
        playlist_generator.SEGMENT_DIR = self._original_segment_dir
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_repeated_call_returns_identical_pdts(self):
        """Calling enhance_playlist twice with identical input must return identical PDTs."""
        first = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        second = playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)
        self.assertEqual(_extract_pdts(first), _extract_pdts(second))

    def test_overlapping_segments_keep_pdts_after_slide(self):
        """When the playlist window slides one position (drop oldest, add newest),
        the overlapping segments must report the EXACT same PDT in both windows.
        """
        # First window: 4 segments
        v1_playlist = SAMPLE_FFMPEG_PLAYLIST
        # Second window: drop the first segment, add a new one at the end.
        # New segment continues the natural cadence: prior segment was epoch
        # 1776250271 with EXTINF 6.037189, so next segment epoch ≈ 1776250277.
        v2_playlist = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:394\n"
            "#EXTINF:5.990744,\n1776250259.ts\n"
            "#EXTINF:5.990756,\n1776250265.ts\n"
            "#EXTINF:6.037189,\n1776250271.ts\n"
            "#EXTINF:5.990744,\n1776250277.ts\n"
        )
        v1 = _extract_pdts(playlist_generator.enhance_playlist(v1_playlist))
        v2 = _extract_pdts(playlist_generator.enhance_playlist(v2_playlist))
        # 1776250259, 1776250265, 1776250271 appear in both windows.
        for fn in ("1776250259.ts", "1776250265.ts", "1776250271.ts"):
            self.assertIn(fn, v1)
            self.assertIn(fn, v2)
            self.assertEqual(
                v1[fn], v2[fn],
                f"PDT for {fn} drifted: {v1[fn]!r} → {v2[fn]!r} after window slide",
            )

    def test_pdt_delta_invariant_preserved_across_slides(self):
        """After a slide, the cached + newly-computed PDTs together must still
        satisfy PDT[i+1] - PDT[i] == EXTINF[i] (existing test_pdt_deltas_equal_extinf
        invariant). Verifies the fix didn't trade one bug for another.
        """
        import datetime as _dt
        playlist_generator.enhance_playlist(SAMPLE_FFMPEG_PLAYLIST)  # populate sidecars
        slid = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:394\n"
            "#EXTINF:5.990744,\n1776250259.ts\n"
            "#EXTINF:5.990756,\n1776250265.ts\n"
            "#EXTINF:6.037189,\n1776250271.ts\n"
            "#EXTINF:5.990744,\n1776250277.ts\n"
        )
        enhanced = playlist_generator.enhance_playlist(slid)
        pdts: list[float] = []
        extinfs: list[float] = []
        for line in enhanced.strip().split("\n"):
            if line.startswith("#EXTINF:"):
                extinfs.append(playlist_generator._parse_extinf(line))
            elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
                ts = line[len("#EXT-X-PROGRAM-DATE-TIME:"):]
                pdts.append(_dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                            .replace(tzinfo=_dt.timezone.utc).timestamp())
        self.assertEqual(len(pdts), 4)
        for i in range(1, len(pdts)):
            self.assertAlmostEqual(pdts[i] - pdts[i - 1], extinfs[i - 1], places=3)


class TestNonAlignedSegments(unittest.TestCase):
    """FFmpeg segments may not align to SEGMENT_DURATION boundaries.
    The enhancer must handle arbitrary epoch filenames correctly."""

    def test_overlapping_filename_epochs_produce_monotonic_pdt(self):
        """When ffmpeg restarts, it may emit segments whose wallclock filenames are
        closer together than the declared EXTINF durations (overlapping in real time).

        Example from a real HAR: filenames 3s/1s/4s apart but each declares ~6s duration.
        The enhancer must still produce PDT values whose deltas == EXTINF, otherwise
        hls.js stalls with "Stuck — no fragment loaded for 15000 ms".
        """
        import datetime as _dt
        playlist = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXTINF:6.037178,\n1776420059.ts\n"
            "#EXTINF:5.990756,\n1776420062.ts\n"  # only 3s after prev — bad wallclock
            "#EXTINF:5.990744,\n1776420063.ts\n"  # only 1s after prev — bad wallclock
            "#EXTINF:5.990756,\n1776420067.ts\n"  # only 4s after prev
        )
        enhanced = playlist_generator.enhance_playlist(playlist)
        pdts: list[float] = []
        for line in enhanced.strip().split("\n"):
            if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
                ts = line[len("#EXT-X-PROGRAM-DATE-TIME:"):]
                pdts.append(_dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                            .replace(tzinfo=_dt.timezone.utc).timestamp())
        self.assertEqual(len(pdts), 4)
        # PDT anchored on the first segment's epoch.
        self.assertAlmostEqual(pdts[0], 1776420059.0, places=2)
        # Each subsequent delta equals the prior declared EXTINF, not the filename gap.
        self.assertAlmostEqual(pdts[1] - pdts[0], 6.037178, places=2)
        self.assertAlmostEqual(pdts[2] - pdts[1], 5.990756, places=2)
        self.assertAlmostEqual(pdts[3] - pdts[2], 5.990744, places=2)


HAVE_APPLE_VALIDATOR = shutil.which("mediastreamvalidator") is not None
HAVE_FFMPEG = shutil.which("ffmpeg") is not None
HAVE_FFPROBE = shutil.which("ffprobe") is not None


STARTUP_OVERLAP_RAW = (
    "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:7\n#EXT-X-MEDIA-SEQUENCE:0\n"
    "#EXTINF:6.037178,\n1776420059.ts\n"
    "#EXTINF:5.990756,\n1776420062.ts\n"
    "#EXTINF:5.990744,\n1776420063.ts\n"
    "#EXTINF:5.990756,\n1776420067.ts\n"
)


def _generate_silence_segment(dest: Path, seconds: int = 6) -> None:
    """Generate a silent AAC mpegts segment with ffmpeg — reused across tests."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(seconds),
            "-c:a", "aac", "-b:a", "64k",
            "-f", "mpegts", str(dest),
        ],
        check=True, timeout=30,
    )


def _build_hls_site(raw_playlist: str, segment_src: Path, parent: Path,
                    target_duration: int = 7) -> Path:
    """Enhance the playlist and materialise it + segments in a fresh directory.

    Returns the workdir containing `index.m3u8` and one <epoch>.ts per segment.
    TARGETDURATION is lifted (RFC 8216 §4.3.3.1 requires >= ceil(max EXTINF)) and
    #EXT-X-ENDLIST is appended so validators treat the playlist as VOD and exit
    instead of polling for live updates.
    """
    enhanced = playlist_generator.enhance_playlist(raw_playlist)
    enhanced = re.sub(
        r"#EXT-X-TARGETDURATION:\d+",
        f"#EXT-X-TARGETDURATION:{target_duration}",
        enhanced,
    )
    if "#EXT-X-ENDLIST" not in enhanced:
        enhanced = enhanced.rstrip("\n") + "\n#EXT-X-ENDLIST\n"

    workdir = Path(tempfile.mkdtemp(dir=parent))
    for match in re.finditer(r"^(\d{10,}\.ts)$", enhanced, re.MULTILINE):
        (workdir / match.group(1)).write_bytes(segment_src.read_bytes())
    (workdir / "index.m3u8").write_text(enhanced)
    return workdir


class _BaseValidatorTest(unittest.TestCase):
    """Shared segment-generation setup for external-tool validators."""

    segment_path: Path
    tmpdir: Path

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix=f"hls_{cls.__name__}_"))
        cls.segment_path = cls.tmpdir / "silence_6s.ts"
        _generate_silence_segment(cls.segment_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)


@unittest.skipUnless(HAVE_APPLE_VALIDATOR, "Apple mediastreamvalidator not installed (HLS Tools .dmg from developer.apple.com)")
@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class TestAppleMediaStreamValidator(_BaseValidatorTest):
    """Feed enhanced playlists through Apple's official HLS validator.

    Verifies that the enhancer produces RFC 8216-compliant playlists:
    monotonic PDT, EXTINF within TARGETDURATION, valid DATERANGE syntax,
    and correctly sequenced segments.

    Skipped automatically when mediastreamvalidator is missing — the tool
    ships in Apple's HTTP Live Streaming Tools package, separate from Xcode.
    The ffprobe-based test class below covers the same invariants when this
    tool isn't available.
    """

    def _run_validator(self, raw_playlist: str, target_duration: int = 7) -> str:
        workdir = _build_hls_site(raw_playlist, self.segment_path, self.tmpdir, target_duration)
        report_dir = workdir / "report"
        report_dir.mkdir()
        proc = subprocess.run(
            ["mediastreamvalidator", "-O", str(report_dir),
             f"file://{workdir / 'index.m3u8'}"],
            capture_output=True, text=True, timeout=120,
        )
        return proc.stdout + "\n" + proc.stderr

    def _assert_no_errors(self, validator_output: str):
        """mediastreamvalidator prefixes spec violations with 'ERROR:'.
        Warnings ('WARNING:') are informational and don't fail the test."""
        error_lines = [line for line in validator_output.splitlines()
                       if "ERROR:" in line]
        self.assertEqual(
            error_lines, [],
            f"Apple mediastreamvalidator flagged errors:\n" + "\n".join(error_lines)
            + f"\n\nFull output:\n{validator_output}",
        )

    def test_sample_playlist_validates(self):
        """The canonical sample playlist, enhanced, must pass Apple's validator."""
        self._assert_no_errors(self._run_validator(SAMPLE_FFMPEG_PLAYLIST))

    def test_startup_overlap_case_validates(self):
        """Regression: the production bug — ffmpeg wrote segments whose wallclock
        filenames were 3s/1s/4s apart while declaring ~6s EXTINF each. The
        un-enhanced playlist would fail validation (overlapping PDTs); the
        enhanced one must pass because PDTs are cumulative from EXTINF."""
        self._assert_no_errors(self._run_validator(STARTUP_OVERLAP_RAW))

    def test_three_segment_playlist_validates(self):
        """Small uniform-6s playlist — simplest possible case."""
        self._assert_no_errors(self._run_validator(SAMPLE_3_SEGMENTS))


@unittest.skipUnless(HAVE_FFPROBE, "ffprobe not installed")
@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class TestFFprobeValidator(_BaseValidatorTest):
    """Fallback validator using ffprobe — always available wherever ffmpeg is.

    ffprobe is a permissive parser, so it catches fewer spec-nits than Apple's
    validator. What it *does* verify end-to-end:
      - The .m3u8 is parseable by a real HLS demuxer.
      - Every referenced segment is reachable.
      - Segments actually demux (valid mpegts containers, recognised codec).
      - Stream duration returned matches the sum of EXTINFs.
    Together with the pure-Python invariant check `test_pdt_deltas_equal_extinf`,
    this gives solid coverage without depending on Apple's binary.
    """

    def _ffprobe(self, raw_playlist: str, target_duration: int = 7) -> tuple[int, str, dict]:
        import json as _json
        workdir = _build_hls_site(raw_playlist, self.segment_path, self.tmpdir, target_duration)
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,codec_name",
                "-of", "json",
                str(workdir / "index.m3u8"),
            ],
            capture_output=True, text=True, timeout=60,
        )
        try:
            data = _json.loads(proc.stdout) if proc.stdout.strip() else {}
        except _json.JSONDecodeError:
            data = {}
        return proc.returncode, proc.stderr, data

    def _assert_clean(self, raw_playlist: str, expected_duration: float):
        code, stderr, data = self._ffprobe(raw_playlist)
        self.assertEqual(code, 0, f"ffprobe exit {code}; stderr:\n{stderr}")
        self.assertEqual(stderr.strip(), "", f"ffprobe emitted errors:\n{stderr}")
        # Duration sanity — ffprobe sums demuxed segment durations.
        self.assertIn("format", data)
        actual = float(data["format"]["duration"])
        self.assertAlmostEqual(actual, expected_duration, delta=0.5,
                               msg=f"Expected ~{expected_duration}s, got {actual}s from ffprobe")
        # At least one audio stream must be present.
        streams = data.get("streams", [])
        self.assertTrue(any(s.get("codec_type") == "audio" for s in streams),
                        f"No audio stream detected in ffprobe output: {streams}")

    def test_sample_playlist_validates(self):
        # Every segment is 6s silence regardless of EXTINF — duration sums to 24s (4 × 6s).
        self._assert_clean(SAMPLE_FFMPEG_PLAYLIST, expected_duration=24.0)

    def test_startup_overlap_case_validates(self):
        """The production-bug playlist must demux cleanly after enhancement."""
        self._assert_clean(STARTUP_OVERLAP_RAW, expected_duration=24.0)

    def test_three_segment_playlist_validates(self):
        self._assert_clean(SAMPLE_3_SEGMENTS, expected_duration=18.0)


if __name__ == "__main__":
    unittest.main()
