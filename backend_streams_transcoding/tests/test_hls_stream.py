"""
HLS stream validation tests.

Tests the live HLS stream against a running container at localhost:8080.
Validates that the playlists and segments are spec-compliant per RFC 8216.

The pod no longer exposes the per-pod `/status.json` or `/metadata/*` HTTP
routes — metadata flows to clients via Django (`/api/v1/stations-metadata`)
populated by `scraper_engine.py`. In-band ID3 is intentionally absent: the
mobile app aligns metadata to audio via `EXT-X-PROGRAM-DATE-TIME` +
timestamped REST polling, not via segment-level ID3.

Usage:
    make dev-stream-test
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8080")


# ── Master playlist ──


class TestMasterPlaylist:
    def test_returns_200(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert r.status_code == 200

    def test_references_media_playlist(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert "index.m3u8" in r.text

    def test_codecs_declared(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert 'CODECS="mp4a.40.5"' in r.text

    def test_no_dangling_audio_group(self):
        """If the STREAM-INF references an AUDIO group, the master must also
        declare it via EXT-X-MEDIA. The simplest spec-compliant master for a
        single-rendition audio-only stream just omits AUDIO entirely — that's
        what we do."""
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        if "AUDIO=" in r.text:
            assert "#EXT-X-MEDIA:" in r.text and "TYPE=AUDIO" in r.text


# ── Live playlists ──


class TestLivePlaylists:
    @pytest.mark.parametrize("path", ["/index.m3u8", "/aac/index.m3u8"])
    def test_returns_200(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=5)
        assert r.status_code == 200

    def test_is_valid_hls(self):
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        assert r.text.startswith("#EXTM3U")
        assert "#EXT-X-VERSION:" in r.text
        assert "#EXT-X-TARGETDURATION:" in r.text
        assert "#EXTINF:" in r.text

    def test_has_ts_segments(self):
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        assert ".ts" in r.text

    def test_no_endlist_for_live(self):
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        assert "#EXT-X-ENDLIST" not in r.text

    def test_has_program_date_time(self):
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        assert "#EXT-X-PROGRAM-DATE-TIME:" in r.text

    def test_aac_index_alias(self):
        """`/aac/index.m3u8` is kept for backward compatibility with the
        in-pod player. It serves the same bytes as `/index.m3u8`."""
        r1 = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        r2 = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert r1.text == r2.text


# ── Segment access ──


class TestSegmentAccess:
    def test_bare_segment(self):
        """Playlist references segments by bare filename; nginx serves them
        from /data/hls/aac/ via the catchall route."""
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/{seg}", timeout=5)
        assert r2.status_code == 200
        assert len(r2.content) > 1000

    def test_segments_start_with_ts_sync_byte(self):
        """A spec-compliant MPEG-TS segment must start with 0x47 (the sync
        byte). Anything prepended before the first 0x47 — e.g. an ID3v2 tag
        — leaves the segment misaligned and confuses strict HLS clients
        (Apple's mediastreamvalidator flags `Segment size = 188*N + R`
        residuals)."""
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/{seg}", timeout=5)
        assert r2.content[:1] == b"\x47", (
            f"Segment {seg} does not start with TS sync byte; "
            f"first 8 bytes = {r2.content[:8]!r}"
        )
        assert len(r2.content) % 188 == 0, (
            f"Segment {seg} length {len(r2.content)} is not a multiple of 188 — "
            f"residual {len(r2.content) % 188} suggests something is being "
            f"prepended or appended outside the TS framing"
        )


# ── Health ──


class TestHealth:
    def test_health(self):
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        assert r.text == "ok"

    def test_player_page(self):
        r = requests.get(f"{BASE_URL}/", timeout=5)
        assert r.status_code == 200
        assert "hls.js" in r.text

    def test_player_html(self):
        r = requests.get(f"{BASE_URL}/player.html", timeout=5)
        assert r.status_code == 200
