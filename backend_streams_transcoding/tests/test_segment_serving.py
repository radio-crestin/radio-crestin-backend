"""
Tests for segment serving: disk, S3 fallback, missing segments, clock alignment.

Runs against a live dev container at localhost:8085.
Requires: make dev (with S3 configured)

Usage:
    python3 -m pytest tests/test_segment_serving.py -v
"""

import os
import time
import requests
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8085")
SEGMENT_DURATION = 6


@pytest.fixture(scope="module")
def live_playlist():
    """Get the current live playlist and parse segment epochs."""
    r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
    assert r.status_code == 200
    lines = r.text.splitlines()
    segments = []
    for line in lines:
        if line.endswith(".ts"):
            epoch = int(line.replace("segments/", "").replace(".ts", ""))
            segments.append(epoch)
    assert len(segments) > 0, "No segments in live playlist"
    return segments


@pytest.fixture(scope="module")
def disk_segments():
    """Get segments actually on disk via status endpoint."""
    r = requests.get(f"{BASE_URL}/status.json", timeout=5)
    assert r.status_code == 200
    data = r.json()
    aac = data.get("aac", {})
    if aac.get("segments_on_disk", 0) == 0:
        pytest.skip("No segments on disk yet")
    return aac


class TestClockAlignment:
    """All segment epochs must be divisible by SEGMENT_DURATION."""

    def test_playlist_segments_are_aligned(self, live_playlist):
        for epoch in live_playlist:
            assert epoch % SEGMENT_DURATION == 0, (
                f"Segment {epoch} is not clock-aligned (epoch % {SEGMENT_DURATION} = {epoch % SEGMENT_DURATION})"
            )

    def test_segments_are_spaced_by_duration(self, live_playlist):
        for i in range(1, min(10, len(live_playlist))):
            diff = live_playlist[i] - live_playlist[i - 1]
            assert diff == SEGMENT_DURATION, (
                f"Gap between segments {live_playlist[i-1]} and {live_playlist[i]}: "
                f"expected {SEGMENT_DURATION}, got {diff}"
            )

    def test_media_sequence_is_deterministic(self, live_playlist):
        """MEDIA-SEQUENCE = first_epoch // SEGMENT_DURATION."""
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        for line in r.text.splitlines():
            if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
                msn = int(line.split(":")[1])
                expected = live_playlist[0] // SEGMENT_DURATION
                assert msn == expected, f"MSN {msn} != expected {expected}"
                return
        pytest.fail("No MEDIA-SEQUENCE found")


class TestDiskSegments:
    """Segments on disk should be served directly by nginx."""

    def test_recent_segment_returns_200(self, live_playlist):
        # The last few segments should be on disk
        seg = live_playlist[-2]  # Not the very last (might be writing)
        r = requests.get(f"{BASE_URL}/aac/segments/{seg}.ts", timeout=5)
        assert r.status_code == 200, f"Segment {seg} returned {r.status_code}"

    def test_segment_has_reasonable_size(self, live_playlist):
        seg = live_playlist[-3]
        r = requests.get(f"{BASE_URL}/aac/segments/{seg}.ts", timeout=5)
        assert r.status_code == 200
        # A 6s AAC segment at 64kbps ≈ 48KB, plus ID3 tag ≈ 50-100KB
        assert len(r.content) > 10000, (
            f"Segment {seg} too small: {len(r.content)} bytes (expected >10KB)"
        )

    def test_segment_has_id3_tag(self, live_playlist):
        seg = live_playlist[-3]
        r = requests.get(f"{BASE_URL}/aac/segments/{seg}.ts", timeout=5)
        assert r.status_code == 200
        assert r.content[:3] == b"ID3", (
            f"Segment {seg} missing ID3 header: {r.content[:3]!r}"
        )

    def test_immutable_cache_header(self, live_playlist):
        seg = live_playlist[-2]
        r = requests.get(f"{BASE_URL}/aac/segments/{seg}.ts", timeout=5)
        cc = r.headers.get("Cache-Control", "")
        assert "immutable" in cc, f"Expected immutable cache, got: {cc}"


class TestMissingSegments:
    """Segments that never existed should return 404."""

    def test_nonexistent_segment_returns_404(self):
        # Use a segment epoch from way in the past
        r = requests.get(f"{BASE_URL}/aac/segments/1700000000.ts", timeout=10)
        assert r.status_code == 404, (
            f"Missing segment returned {r.status_code} (expected 404)"
        )

    def test_gap_segment_returns_404(self, disk_segments):
        """A segment in the gap between container restarts should return 404."""
        oldest = disk_segments.get("oldest_on_disk", 0)
        if oldest == 0:
            pytest.skip("No disk segments")
        # Try 1 hour before the oldest disk segment — definitely a gap
        gap_seg = ((oldest - 3600) // SEGMENT_DURATION) * SEGMENT_DURATION
        r = requests.get(f"{BASE_URL}/aac/segments/{gap_seg}.ts", timeout=10)
        assert r.status_code == 404, (
            f"Gap segment {gap_seg} returned {r.status_code} (expected 404)"
        )

    def test_missing_segment_is_fast(self):
        """Missing segment 404 should return quickly (not hang)."""
        seg = 1700000000
        start = time.time()
        r = requests.get(f"{BASE_URL}/aac/segments/{seg}.ts", timeout=10)
        elapsed = time.time() - start
        assert r.status_code == 404
        assert elapsed < 5, f"Missing segment took {elapsed:.1f}s (should be fast)"


class TestTimestampedPlayback:
    """Timestamp-based playlist generation."""

    def test_snaps_to_segment_boundary(self):
        # Use a non-aligned timestamp
        ts = 1776181001  # 1776181001 % 6 = 5, should snap to 1776180996
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={ts}", timeout=5)
        assert r.status_code == 200
        lines = r.text.splitlines()
        first_seg = [l for l in lines if l.endswith(".ts")][0]
        epoch = int(first_seg.replace("segments/", "").replace(".ts", ""))
        expected = ts - (ts % SEGMENT_DURATION)
        assert epoch == expected, f"Expected snap to {expected}, got {epoch}"

    def test_different_timestamps_produce_different_playlists(self):
        ts1 = 1776172728
        ts2 = 1776173004
        r1 = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={ts1}", timeout=5)
        r2 = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={ts2}", timeout=5)
        segs1 = [l for l in r1.text.splitlines() if l.endswith(".ts")]
        segs2 = [l for l in r2.text.splitlines() if l.endswith(".ts")]
        assert segs1[0] != segs2[0], (
            f"Both timestamps produced same first segment: {segs1[0]}"
        )
