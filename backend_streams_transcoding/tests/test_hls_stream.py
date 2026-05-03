"""
HLS stream validation tests.

Tests the live HLS stream against a running container at localhost:8080.
Validates playlists, segments, and metadata.

Usage:
    make dev-stream-test
"""

import time

import pytest
import requests

BASE_URL = "http://localhost:8080"


# ── Fixtures ──


@pytest.fixture(scope="module")
def status():
    resp = requests.get(f"{BASE_URL}/status.json", timeout=5)
    assert resp.status_code == 200
    return resp.json()


# ── Master playlist ──


class TestMasterPlaylist:
    def test_returns_200(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert r.status_code == 200

    def test_contains_aac_variant(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert "aac/index.m3u8" in r.text

    def test_codecs_declared(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert 'CODECS="mp4a.40.5"' in r.text


# ── Live playlists ──


class TestLivePlaylists:
    @pytest.mark.parametrize("path", ["/index.m3u8", "/aac/index.m3u8"])
    def test_returns_200(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=5)
        assert r.status_code == 200

    def test_is_valid_hls(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert r.text.startswith("#EXTM3U")
        assert "#EXT-X-VERSION:" in r.text
        assert "#EXT-X-TARGETDURATION:" in r.text
        assert "#EXTINF:" in r.text

    def test_aac_has_ts_segments(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert ".ts" in r.text

    def test_no_endlist_for_live(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert "#EXT-X-ENDLIST" not in r.text

    def test_has_program_date_time(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert "#EXT-X-PROGRAM-DATE-TIME:" in r.text

    def test_backward_compat_index(self):
        r1 = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        r2 = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert r1.status_code == 200
        # Both should return AAC segments
        assert ".ts" in r1.text


# ── Segment access ──


class TestSegmentAccess:
    def test_aac_segment(self, status):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/aac/{seg}", timeout=5)
        assert r2.status_code == 200
        assert len(r2.content) > 1000

    def test_compat_segment(self):
        """Segments at /segments/*.ts (for /index.m3u8 backward compat)."""
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/{seg}", timeout=5)
        assert r2.status_code == 200


# ── Status & availability ──


class TestStatus:
    def test_status_json(self):
        r = requests.get(f"{BASE_URL}/status.json", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "aac" in data
        assert data["aac"]["segments_on_disk"] >= 0


# ── Metadata ──


class TestMetadata:
    def test_metadata_index_exists(self):
        r = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "current" in data
        assert "recent" in data
        assert "updated_at" in data

    def test_current_song_has_fields(self):
        r = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
        data = r.json()
        cur = data["current"]
        assert "title" in cur
        assert "artist" in cur
        assert "raw" in cur
        assert "started_at" in cur
        assert "started_at_iso" in cur

    def test_current_song_detected(self):
        """Metadata monitor should detect the station's ICY metadata."""
        # Wait briefly for metadata monitor to pick up the stream title
        for _ in range(10):
            r = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
            data = r.json()
            if data["current"].get("raw"):
                break
            time.sleep(1)
        assert data["current"]["raw"], "No song detected — ICY metadata not received"
        assert data["current"]["started_at"] > 1700000000, "Invalid started_at epoch"

    def test_status_includes_metadata(self):
        r = requests.get(f"{BASE_URL}/status.json", timeout=5)
        data = r.json()
        assert "metadata" in data
        assert data["metadata"] is not None
        assert "current" in data["metadata"]

    def test_status_includes_pod_started_at(self):
        r = requests.get(f"{BASE_URL}/status.json", timeout=5)
        data = r.json()
        assert "pod_started_at" in data
        assert data["pod_started_at"] > 1700000000

    def test_playlist_has_daterange_tags(self):
        """Playlist should contain EXT-X-DATERANGE with song metadata
        once a song has been detected. Verifies the AVPlayer-friendly
        format (no CLASS, no DURATION)."""
        # Wait for metadata monitor to detect a song
        for _ in range(15):
            r = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
            if r.json().get("current", {}).get("raw"):
                break
            time.sleep(1)

        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        if "#EXT-X-DATERANGE:" in r.text:
            assert "X-TITLE=" in r.text
            # CLASS triggers AVPlayer interstitial / ad behavior; must be absent.
            assert "CLASS=" not in r.text, (
                "DATERANGE must not include CLASS — it disrupts AVPlayer playback"
            )
            # DURATION makes AVPlayer treat the range as a hard end.
            assert "DURATION=" not in r.text, (
                "DATERANGE must not include DURATION — it triggers seeks on AVPlayer"
            )
        else:
            # Song might not overlap with current live window yet
            pytest.skip("No DATERANGE yet — song start may be outside live window")

    def test_segments_have_id3_tags(self):
        """AAC .ts segments should have ID3v2 tags prepended."""
        # Get a segment URL from the playlist
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/aac/{seg}", timeout=5)
        assert r2.status_code == 200
        # Check for ID3 header (bytes 0x49 0x44 0x33 = "ID3")
        assert r2.content[:3] == b"ID3", (
            f"Segment {seg} missing ID3 tag — first 3 bytes: {r2.content[:3]!r}"
        )
        # Verify it's v2.4
        assert r2.content[3] == 4, f"Expected ID3v2.4, got v2.{r2.content[3]}"

    def test_id3_contains_title(self):
        """ID3 tag should contain TIT2 (title) frame."""
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/aac/{seg}", timeout=5)
        # Find TIT2 frame in first 500 bytes
        assert b"TIT2" in r2.content[:500], "No TIT2 frame in ID3 tag"
        assert b"TPE1" in r2.content[:500], "No TPE1 frame in ID3 tag"

    def test_metadata_updates_over_time(self):
        """updated_at should advance on each poll."""
        r1 = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
        t1 = r1.json()["updated_at"]
        time.sleep(11)  # Index updates every 10s
        r2 = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
        t2 = r2.json()["updated_at"]
        assert t2 > t1, f"updated_at didn't advance: {t1} -> {t2}"


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
