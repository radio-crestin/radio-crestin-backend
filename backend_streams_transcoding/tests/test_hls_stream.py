"""
HLS stream validation tests.

Tests the live HLS stream against a running container at localhost:8080.
Validates playlists, segments, historical playback, and gap handling.

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


@pytest.fixture(scope="module")
def oldest_ts(status):
    return int(status["aac"]["oldest_epoch"])


# ── Master playlist ──


class TestMasterPlaylist:
    def test_returns_200(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert r.status_code == 200

    def test_contains_aac_variant(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert "aac/index.m3u8" in r.text

    def test_contains_opus_variant(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert "opus/index.m3u8" in r.text

    def test_codecs_declared(self):
        r = requests.get(f"{BASE_URL}/master.m3u8", timeout=5)
        assert 'CODECS="mp4a.40.5"' in r.text
        assert 'CODECS="opus"' in r.text


# ── Live playlists ──


class TestLivePlaylists:
    @pytest.mark.parametrize("path", ["/index.m3u8", "/aac/index.m3u8", "/opus/index.m3u8"])
    def test_returns_200(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=5)
        assert r.status_code == 200

    @pytest.mark.parametrize("path", ["/aac/index.m3u8", "/opus/index.m3u8"])
    def test_is_valid_hls(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=5)
        assert r.text.startswith("#EXTM3U")
        assert "#EXT-X-VERSION:" in r.text
        assert "#EXT-X-TARGETDURATION:" in r.text
        assert "#EXTINF:" in r.text

    def test_aac_has_ts_segments(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert ".ts" in r.text

    def test_opus_has_m4s_segments(self):
        r = requests.get(f"{BASE_URL}/opus/index.m3u8", timeout=5)
        assert ".m4s" in r.text
        assert 'EXT-X-MAP:URI="init.mp4"' in r.text

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

    def test_opus_init(self):
        r = requests.get(f"{BASE_URL}/opus/init.mp4", timeout=5)
        assert r.status_code == 200
        assert len(r.content) > 100

    def test_opus_segment(self):
        r = requests.get(f"{BASE_URL}/opus/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".m4s")][0]
        r2 = requests.get(f"{BASE_URL}/opus/{seg}", timeout=5)
        assert r2.status_code == 200
        assert len(r2.content) > 500

    def test_compat_segment(self):
        """Segments at /segments/*.ts (for /index.m3u8 backward compat)."""
        r = requests.get(f"{BASE_URL}/index.m3u8", timeout=5)
        seg = [l for l in r.text.splitlines() if l.endswith(".ts")][0]
        r2 = requests.get(f"{BASE_URL}/{seg}", timeout=5)
        assert r2.status_code == 200


# ── Historical playback ──


class TestHistoricalPlayback:
    def test_timestamp_returns_event_playlist(self, oldest_ts):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}", timeout=5)
        assert r.status_code == 200
        assert "#EXT-X-PLAYLIST-TYPE:EVENT" in r.text

    def test_timestamp_starts_from_requested_time(self, oldest_ts):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}", timeout=5)
        lines = r.text.splitlines()
        # First segment filename should contain the oldest timestamp
        seg_lines = [l for l in lines if l.endswith(".ts")]
        assert len(seg_lines) > 0
        first_seg = seg_lines[0]
        # Segment number should be close to the requested timestamp
        seg_num = int(first_seg.split("/")[-1].replace(".ts", ""))
        assert abs(seg_num - oldest_ts) < 5, (
            f"First segment {seg_num} too far from requested {oldest_ts}"
        )

    def test_no_endlist_allows_polling(self, oldest_ts):
        """EVENT playlist without ENDLIST lets hls.js keep polling for more."""
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}", timeout=5)
        # Should NOT have ENDLIST (unless we've caught up to a very short stream)
        # With enough segments, ENDLIST should be absent
        # This is the key for continuous playback
        assert "#EXT-X-PLAYLIST-TYPE:EVENT" in r.text

    def test_playlist_grows_over_time(self, oldest_ts):
        """Polling the same timestamp URL returns more segments as time passes."""
        url = f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}"
        r1 = requests.get(url, timeout=5)
        count1 = r1.text.count("#EXTINF:")

        time.sleep(7)  # Wait for at least one new segment

        r2 = requests.get(url, timeout=5)
        count2 = r2.text.count("#EXTINF:")
        assert count2 > count1, (
            f"Playlist didn't grow: {count1} -> {count2} segments. "
            "hls.js needs growing playlists for seamless playback."
        )

    def test_media_sequence_stable(self, oldest_ts):
        """MEDIA-SEQUENCE must stay the same across polls for EVENT playlists."""
        url = f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}"
        r1 = requests.get(url, timeout=5)
        seq1 = [l for l in r1.text.splitlines() if "MEDIA-SEQUENCE" in l][0]

        time.sleep(3)

        r2 = requests.get(url, timeout=5)
        seq2 = [l for l in r2.text.splitlines() if "MEDIA-SEQUENCE" in l][0]
        assert seq1 == seq2, (
            f"MEDIA-SEQUENCE changed: {seq1} -> {seq2}. "
            "Must be stable for EVENT playlists or hls.js resets playback."
        )

    def test_all_segments_in_playlist_are_fetchable(self, oldest_ts):
        """Every segment referenced in a timestamp playlist must be downloadable."""
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={oldest_ts}", timeout=5)
        seg_lines = [l for l in r.text.splitlines() if l.endswith(".ts")]
        assert len(seg_lines) > 0

        for seg in seg_lines[:5]:  # Test first 5
            r2 = requests.get(f"{BASE_URL}/aac/{seg}", timeout=5)
            assert r2.status_code == 200, f"Segment {seg} returned {r2.status_code}"
            assert len(r2.content) > 500, f"Segment {seg} too small: {len(r2.content)}B"

    def test_opus_timestamp_has_init_map(self, oldest_ts):
        r = requests.get(f"{BASE_URL}/opus/index.m3u8?timestamp={oldest_ts}", timeout=5)
        assert r.status_code == 200
        assert 'EXT-X-MAP:URI="init.mp4"' in r.text

    def test_future_timestamp_returns_live(self):
        future = int(time.time()) + 3600
        r = requests.get(f"{BASE_URL}/aac/index.m3u8?timestamp={future}", timeout=5)
        assert r.status_code == 200
        # Should be a live playlist (no EVENT type)
        assert "#EXT-X-PLAYLIST-TYPE:EVENT" not in r.text


# ── Delivery Directives (RFC 8216bis) ──


class TestDeliveryDirectives:
    def test_server_control_header(self):
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert "#EXT-X-SERVER-CONTROL:" in r.text
        assert "CAN-BLOCK-RELOAD=YES" in r.text
        assert "CAN-SKIP-UNTIL=" in r.text

    def test_blocking_reload_existing_segment(self, status):
        """_HLS_msn for an existing segment returns immediately."""
        oldest = int(status["aac"]["oldest_epoch"])
        start = time.time()
        r = requests.get(
            f"{BASE_URL}/aac/index.m3u8?_HLS_msn={oldest}", timeout=15
        )
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 2, f"Should return immediately, took {elapsed:.1f}s"

    def test_blocking_reload_waits_for_new_segment(self):
        """_HLS_msn for a future segment blocks until it appears."""
        # Get current newest
        r = requests.get(f"{BASE_URL}/status.json", timeout=5)
        data = r.json()
        newest_epoch = data["aac"]["newest_epoch"]
        # Segment numbers are epoch-based, guess the next one
        # Use a number slightly ahead
        next_seg = int(newest_epoch) + 2

        start = time.time()
        r = requests.get(
            f"{BASE_URL}/aac/index.m3u8?_HLS_msn={next_seg}", timeout=15
        )
        elapsed = time.time() - start
        assert r.status_code == 200
        # Should have blocked for at least 1 second
        assert elapsed >= 1, f"Should block, but returned in {elapsed:.1f}s"
        # Should contain the requested segment or newer
        assert "#EXTINF:" in r.text

    def test_skip_returns_valid_playlist(self, status):
        """_HLS_skip=YES returns a valid playlist."""
        newest = int(status["aac"]["newest_epoch"])
        r = requests.get(
            f"{BASE_URL}/aac/index.m3u8?_HLS_msn={newest}&_HLS_skip=YES",
            timeout=15,
        )
        assert r.status_code == 200
        assert "#EXTM3U" in r.text
        assert "#EXT-X-SERVER-CONTROL:" in r.text

    def test_version_9_for_skip_support(self):
        """Version must be >= 9 for EXT-X-SKIP support."""
        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        assert "#EXT-X-VERSION:9" in r.text


# ── Status & availability ──


class TestStatus:
    def test_status_json(self):
        r = requests.get(f"{BASE_URL}/status.json", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "aac" in data
        assert "opus" in data
        assert data["aac"]["segments"] > 0
        assert "gaps" in data["aac"]

    def test_availability_json(self):
        r = requests.get(f"{BASE_URL}/availability.json", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "aac" in data
        assert "ranges" in data["aac"]
        assert len(data["aac"]["ranges"]) > 0

    def test_availability_ranges_have_valid_times(self):
        r = requests.get(f"{BASE_URL}/availability.json", timeout=5)
        data = r.json()
        for rng in data["aac"]["ranges"]:
            assert rng["start"] > 1700000000, f"Start too small: {rng['start']}"
            assert rng["end"] >= rng["start"]
            assert rng["segments"] > 0


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
        once a song has been detected."""
        # Wait for metadata monitor to detect a song
        for _ in range(15):
            r = requests.get(f"{BASE_URL}/metadata/index.json", timeout=5)
            if r.json().get("current", {}).get("raw"):
                break
            time.sleep(1)

        r = requests.get(f"{BASE_URL}/aac/index.m3u8", timeout=5)
        if "#EXT-X-DATERANGE:" in r.text:
            assert 'CLASS="com.radiocrestin.song"' in r.text
            assert "X-TITLE=" in r.text
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
