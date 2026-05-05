"""Regression tests for the HLS playlist rewriter.

The rewriter copies ffmpeg's live.m3u8 to index.m3u8, injecting
EXT-X-DATERANGE song-metadata tags from /data/metadata/index.json. The
non-trivial bit is the cutoff: a DATERANGE must NOT be removed from the
playlist while its time range still overlaps any segment in the
playlist, or Apple's mediastreamvalidator flags
  "Removed an EXT-X-DATERANGE while mapped to range in playlist"
which AVPlayer actually surfaces as playback-blocking on iOS.

These tests exercise the multi-fetch scenario the original implementation
got wrong: a wall-clock cutoff dropped a song whose time range still
overlapped the live playlist on a subsequent rewriter pass.
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import playlist_rewriter  # noqa: E402


def _make_playlist(first_pdt_epoch: float, count: int = 5) -> str:
    """Build a minimal ffmpeg-style playlist with `count` segments starting
    at the given PDT epoch, 6s each."""
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        "#EXT-X-TARGETDURATION:6",
        f"#EXT-X-MEDIA-SEQUENCE:{int(first_pdt_epoch)}",
    ]
    for i in range(count):
        seg_pdt = first_pdt_epoch + i * 6
        # ISO 8601 with millisecond precision (matches ffmpeg's output)
        iso = time.strftime(
            "%Y-%m-%dT%H:%M:%S.000+0000", time.gmtime(seg_pdt)
        )
        lines.append("#EXTINF:6.000000,")
        lines.append(f"#EXT-X-PROGRAM-DATE-TIME:{iso}")
        lines.append(f"seg-{int(seg_pdt)}.ts")
    return "\n".join(lines) + "\n"


def _song(started_at: float, title: str, artist: str = "A") -> dict:
    return {"started_at": started_at, "title": title, "artist": artist, "raw": title}


class TestEarliestPDT(unittest.TestCase):
    def test_earliest_pdt_picks_smallest(self):
        raw = _make_playlist(1700000000, count=3)
        ep = playlist_rewriter._earliest_segment_pdt_epoch(raw)
        self.assertEqual(ep, 1700000000)

    def test_no_pdt_returns_none(self):
        raw = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n"
        self.assertIsNone(playlist_rewriter._earliest_segment_pdt_epoch(raw))

    def test_handles_z_suffix(self):
        raw = (
            "#EXTM3U\n#EXT-X-PROGRAM-DATE-TIME:2026-05-05T07:00:00.000Z\n"
            "seg-1.ts\n"
        )
        ep = playlist_rewriter._earliest_segment_pdt_epoch(raw)
        self.assertIsNotNone(ep)


class TestEnhanceCutoff(unittest.TestCase):
    """Reproduces the production validator failure mode: a song's
    DATERANGE must not vanish on a later rewriter pass while the playlist
    still has segments inside that song's time range."""

    def test_song_within_window_kept(self):
        # Playlist covers [t, t+24]. Song started at t+5 → in range.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "in-window")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="in-window"', out)

    def test_song_before_earliest_pdt_dropped_unless_most_recent(self):
        # Playlist covers [t, t+24]. Song A started at t-100 (behind window),
        # song B at t+5 (in window). Latest = B. A's active range is
        # [t-100, t+5] which still OVERLAPS the playlist (t+5 > earliest_pdt
        # = t), so A must NOT be dropped — it's still mapped.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t - 100, "old"), _song(t + 5, "current")]
        out = playlist_rewriter.enhance(raw, songs)
        # Both kept: old's range overlaps the playlist via its successor's start.
        self.assertIn('X-TITLE="old"', out)
        self.assertIn('X-TITLE="current"', out)

    def test_song_truly_evicted_when_successor_also_behind_window(self):
        # 3-song scenario: A@t-200 → B@t-100 → C@t+5.
        # Playlist starts at t (cutoff ≈ t-2). A's range [t-200, t-100]
        # ends at t-100 ≤ cutoff → A is fully behind the playlist → DROP.
        # B's range [t-100, t+5] ends at t+5 > cutoff → still mapped → KEEP.
        # C is the latest → KEEP.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [
            _song(t - 200, "A-truly-old"),
            _song(t - 100, "B-still-mapped"),
            _song(t + 5, "C-current"),
        ]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertNotIn('X-TITLE="A-truly-old"', out)
        self.assertIn('X-TITLE="B-still-mapped"', out)
        self.assertIn('X-TITLE="C-current"', out)

    def test_most_recent_song_always_kept_even_if_before_window(self):
        # Long-running song scenario: a song started before the playlist
        # window AND is still the latest (no newer song yet). AVPlayer
        # needs the DATERANGE to render "now playing" — must not drop.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t - 600, "long-running-current")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="long-running-current"', out)

    def test_no_pdt_in_playlist_keeps_all(self):
        # Warmup: ffmpeg has just started writing the playlist, no PDT
        # lines yet. Without a cutoff anchor, keep everything.
        raw = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n"
        songs = [_song(1700000000, "first")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="first"', out)

    def test_version_bumped_to_6_when_daterange_emitted(self):
        # DATERANGE was added in HLS v6 (RFC 8216 §4.4.5.1); a v3 playlist
        # carrying DATERANGE is technically invalid.
        t = 1700000000
        raw = _make_playlist(t, count=3)
        self.assertIn("#EXT-X-VERSION:3", raw)
        out = playlist_rewriter.enhance(raw, [_song(t + 1, "song")])
        self.assertIn("#EXT-X-VERSION:6", out)
        self.assertNotIn("#EXT-X-VERSION:3", out)

    def test_no_songs_passes_through_unchanged(self):
        t = 1700000000
        raw = _make_playlist(t, count=3)
        out = playlist_rewriter.enhance(raw, [])
        self.assertEqual(raw, out)


class TestMultipleFetchScenario(unittest.TestCase):
    """The exact failure mode that broke production:
    - At time T1, the live playlist's earliest PDT is P1 and song S
      started at T1-30s (inside the playlist's time range).
    - The rewriter emits DATERANGE for S.
    - At time T2 > T1, the playlist has rolled. Earliest PDT is now P2 > S.start.
    - On the second rewriter pass, S must STILL be emitted as long as
      its range still overlaps the playlist, otherwise mediastreamvalidator
      flags "Removed an EXT-X-DATERANGE while mapped".
    - S only stops being emitted once P2 > S.start AND a newer song exists
      AND S's range is entirely behind the playlist.
    """

    def test_song_persists_until_truly_evicted(self):
        # T=0: playlist [t, t+24], song S started at t+5
        t = 1700000000
        s_started = t + 5
        songs = [_song(s_started, "S")]

        # First pass: S is in range → emitted.
        raw1 = _make_playlist(t, count=5)
        out1 = playlist_rewriter.enhance(raw1, songs)
        self.assertIn('X-TITLE="S"', out1)

        # T=12: playlist now [t+12, t+36]. S started at t+5, before earliest.
        # But S is still the only/most-recent song → must still be emitted.
        raw2 = _make_playlist(t + 12, count=5)
        out2 = playlist_rewriter.enhance(raw2, songs)
        self.assertIn('X-TITLE="S"', out2)

        # T=60, with a newer song S2 starting at t+30: playlist now
        # [t+60, t+84]. S's range = [t+5, t+30]. Successor (S2) start = t+30
        # ≤ earliest_pdt (t+60) − 2 → S's active range is fully behind the
        # playlist → DROP. S2 is the latest → KEEP.
        songs_after = [_song(s_started, "S"), _song(t + 30, "S2")]
        raw3 = _make_playlist(t + 60, count=5)
        out3 = playlist_rewriter.enhance(raw3, songs_after)
        self.assertNotIn('X-TITLE="S"', out3)
        self.assertIn('X-TITLE="S2"', out3)

    def test_non_latest_songs_have_end_date(self):
        # AVPlayer's validator treats a DATERANGE without END-DATE /
        # DURATION / END-ON-NEXT as having UNKNOWN duration (effectively
        # unbounded forward). Removing such a tag from a later playlist
        # response triggers "Removed an EXT-X-DATERANGE while mapped to
        # range in playlist" even when no playlist segment overlaps the
        # song's actual airtime. Bound non-latest songs with END-DATE.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "older"), _song(t + 100, "current")]
        out = playlist_rewriter.enhance(raw, songs)
        # "older" has a successor → must carry END-DATE.
        older_line = next(
            ln for ln in out.split("\n") if 'X-TITLE="older"' in ln
        )
        self.assertIn("END-DATE=", older_line)
        # "current" is the latest → unbounded, no END-DATE.
        current_line = next(
            ln for ln in out.split("\n") if 'X-TITLE="current"' in ln
        )
        self.assertNotIn("END-DATE=", current_line)

    def test_three_songs_middle_one_kept_while_active_range_overlaps(self):
        # Reproduces the *exact* failure mode that surfaced on the
        # production validator after the first cutoff rewrite:
        #
        #   recent = [A@t-200, B@t-100, C@t+5]
        #   playlist's earliest PDT = t
        #
        # With the buggy "drop if own_start < cutoff && not most_recent"
        # rule, B was dropped — but B's *active range* [t-100, t+5] still
        # overlaps the playlist (because successor C starts at t+5 > t),
        # so removing B's DATERANGE while still mapped triggers
        # "Removed an EXT-X-DATERANGE while mapped to range in playlist".
        #
        # The successor-aware rule keeps B until *its successor* C also
        # starts before the playlist window.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [
            _song(t - 200, "A"),
            _song(t - 100, "B"),
            _song(t + 5, "C"),
        ]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertNotIn('X-TITLE="A"', out, "A's range ends at t-100, fully before playlist → safe to drop")
        self.assertIn('X-TITLE="B"', out, "B's range ends at t+5 (still mapped) → MUST be kept")
        self.assertIn('X-TITLE="C"', out, "C is the latest → always kept")


if __name__ == "__main__":
    unittest.main()
