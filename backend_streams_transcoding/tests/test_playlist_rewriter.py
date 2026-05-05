"""Regression tests for the HLS playlist rewriter.

The rewriter copies ffmpeg's live.m3u8 to index.m3u8, injecting
EXT-X-DATERANGE song-metadata tags from /data/metadata/index.json.

Apple's mediastreamvalidator (and AVPlayer's metadata collector) imposes
two strict rules that drove the design:

  R1. Once a DATERANGE is published, the Server MUST NOT change any of
      its attributes (RFC 8216 §4.4.5.1.1). So a DATERANGE's END-DATE
      cannot be added later — must be set on first emission.

  R2. A DATERANGE MUST NOT be removed from the playlist while still
      "mapped to range in playlist" — i.e. while its time range
      overlaps any segment in the playlist. A DATERANGE without
      DURATION / END-DATE / END-ON-NEXT has unknown duration per
      §4.4.5.1, which AVPlayer treats as unbounded forward — making
      removal a violation forever.

Combined consequence in a *livestream* context (no known song end at
emission time): only emit DATERANGE for songs that have already ENDED
(have a successor in the buffer). The current "now playing" song gets
no DATERANGE — its metadata still reaches clients via the existing
PROGRAM-DATE-TIME + REST-poll path.
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


class TestEnhance(unittest.TestCase):
    def test_current_song_alone_is_not_emitted(self):
        # Only one song known → no successor → no DATERANGE. The current
        # song's metadata reaches clients via PROGRAM-DATE-TIME + REST.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        out = playlist_rewriter.enhance(raw, [_song(t + 5, "current-only")])
        self.assertNotIn('X-TITLE="current-only"', out)
        # Playlist passes through unchanged when no DATERANGE is emitted.
        self.assertEqual(raw, out)

    def test_two_songs_only_past_emitted(self):
        # A is past (has successor B). B is current. Emit only A, with
        # END-DATE = B.start (committed once).
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "past-A"), _song(t + 100, "current-B")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="past-A"', out)
        self.assertNotIn('X-TITLE="current-B"', out)

        a_line = next(l for l in out.split("\n") if 'X-TITLE="past-A"' in l)
        self.assertIn("END-DATE=", a_line)
        # END-DATE must equal B.start (millisecond-precision ISO 8601).
        expected_end_iso = playlist_rewriter._epoch_to_pdt(t + 100)
        self.assertIn(f'END-DATE="{expected_end_iso}"', a_line)

    def test_song_dropped_when_range_entirely_behind_playlist(self):
        # A's range is [t-200, t-100]. Earliest playlist PDT = t →
        # cutoff = t - 2. Successor B starts at t-100, which is ≤ cutoff
        # → A's range fully behind playlist → DROP.
        # B currently exists with successor C at t+5 → emit B with
        # END-DATE = t+5 (overlaps playlist). C is current → not emitted.
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
        self.assertNotIn('X-TITLE="C-current"', out)

    def test_no_pdt_in_playlist_keeps_all_past_songs(self):
        # Warmup: ffmpeg has just started writing the playlist, no PDT
        # lines yet. Without a cutoff anchor, keep every past song;
        # current still skipped (no successor → no end committed).
        raw = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:6\n"
        songs = [_song(1700000000, "first"), _song(1700000200, "second")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="first"', out)
        self.assertNotIn('X-TITLE="second"', out)

    def test_version_bumped_to_6_when_daterange_emitted(self):
        # DATERANGE was added in HLS v6 (RFC 8216 §4.4.5.1); a v3 playlist
        # carrying DATERANGE is technically invalid.
        t = 1700000000
        raw = _make_playlist(t, count=3)
        self.assertIn("#EXT-X-VERSION:3", raw)
        out = playlist_rewriter.enhance(
            raw, [_song(t + 1, "past"), _song(t + 50, "current")]
        )
        self.assertIn("#EXT-X-VERSION:6", out)
        self.assertNotIn("#EXT-X-VERSION:3", out)

    def test_no_songs_passes_through_unchanged(self):
        t = 1700000000
        raw = _make_playlist(t, count=3)
        out = playlist_rewriter.enhance(raw, [])
        self.assertEqual(raw, out)


class TestImmutableAttributes(unittest.TestCase):
    """RFC 8216 §4.4.5.1.1: a Server MUST NOT change any attribute of a
    published DATERANGE. Re-emitting the same ID across rewriter passes
    must produce byte-identical attribute sets."""

    def test_same_inputs_produce_byte_identical_daterange(self):
        # Same playlist + same song list → same DATERANGE on every call.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "past"), _song(t + 100, "current")]
        out_a = playlist_rewriter.enhance(raw, songs)
        out_b = playlist_rewriter.enhance(raw, songs)
        self.assertEqual(out_a, out_b)

    def test_past_song_attributes_stable_across_window_slides(self):
        # As the playlist window slides forward, the SAME song's DATERANGE
        # must keep the same ID + START-DATE + END-DATE. Only when its
        # range is entirely behind the new earliest PDT does it drop —
        # but its attributes never change while present.
        t = 1700000000
        songs = [_song(t + 5, "A"), _song(t + 100, "B"), _song(t + 200, "C-current")]

        raw1 = _make_playlist(t, count=5)
        raw2 = _make_playlist(t + 30, count=5)  # window slid 30s

        out1 = playlist_rewriter.enhance(raw1, songs)
        out2 = playlist_rewriter.enhance(raw2, songs)

        a_in_1 = next((l for l in out1.split("\n") if 'X-TITLE="A"' in l), None)
        a_in_2 = next((l for l in out2.split("\n") if 'X-TITLE="A"' in l), None)
        self.assertIsNotNone(a_in_1)
        self.assertIsNotNone(a_in_2)
        self.assertEqual(a_in_1, a_in_2)

        b_in_1 = next((l for l in out1.split("\n") if 'X-TITLE="B"' in l), None)
        b_in_2 = next((l for l in out2.split("\n") if 'X-TITLE="B"' in l), None)
        self.assertIsNotNone(b_in_1)
        self.assertIsNotNone(b_in_2)
        self.assertEqual(b_in_1, b_in_2)

    def test_current_song_never_emitted_with_or_without_successor(self):
        # The "current" song is always the largest-START-DATE entry.
        # Whether the buffer holds 1 or 5 songs, the current is excluded.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        for n in (1, 2, 3, 5):
            songs = [_song(t + 10 * (i + 1), f"song-{i}") for i in range(n)]
            current_title = f"song-{n - 1}"
            out = playlist_rewriter.enhance(raw, songs)
            self.assertNotIn(
                f'X-TITLE="{current_title}"', out,
                f"current song must never be emitted (n={n})"
            )


if __name__ == "__main__":
    unittest.main()
