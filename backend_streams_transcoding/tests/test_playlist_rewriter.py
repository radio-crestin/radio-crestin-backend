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
    def test_current_song_alone_is_not_emitted_as_daterange(self):
        # Only one song known → no successor → no DATERANGE for it. The
        # current song's full metadata still reaches clients via REST,
        # but the EXT-X-RC-METADATA-CHANGED marker IS emitted (carries
        # only its started_at, not title/artist) so mobile knows a
        # current-song change happened in the source.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        out = playlist_rewriter.enhance(raw, [_song(t + 5, "current-only")])
        self.assertNotIn('X-TITLE="current-only"', out)
        # Marker reflects the current song's epoch.
        self.assertIn(f"#EXT-X-RC-METADATA-CHANGED:", out)
        self.assertIn(f"EPOCH={int(t + 5)}", out)

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


class TestMetadataChangedMarker(unittest.TestCase):
    """EXT-X-RC-METADATA-CHANGED is the real-time current-song-change
    signal mobile uses to schedule a metadata refresh aligned to the
    playback timeline (important when the user is seeking behind live
    edge by 2-4 minutes).

    Compatibility: per RFC 8216 §4.1, unknown tags MUST be ignored. So
    this tag is invisible to AVPlayer / ExoPlayer / hls.js / older app
    versions — safe to deploy without coordinated client release.
    """

    def test_marker_reflects_largest_started_at(self):
        # The current song is whichever entry has the largest started_at.
        # Marker must carry that song's epoch — not the most recently
        # appended entry, not the smallest, not now().
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [
            _song(t + 200, "should-be-current"),
            _song(t + 5, "older"),
            _song(t + 100, "in-between"),
        ]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn(f"EPOCH={int(t + 200)}", out)
        self.assertNotIn(f"EPOCH={int(t + 5)}", out)
        self.assertNotIn(f"EPOCH={int(t + 100)}", out)

    def test_marker_value_changes_when_current_song_changes(self):
        # The whole point: when the current song flips, the marker
        # value flips, and mobile detects the change between polls.
        t = 1700000000
        raw = _make_playlist(t, count=5)

        out_a = playlist_rewriter.enhance(raw, [_song(t + 5, "song-A")])
        out_b = playlist_rewriter.enhance(raw, [_song(t + 5, "song-A"),
                                                _song(t + 100, "song-B")])

        self.assertIn(f"EPOCH={int(t + 5)}", out_a)
        self.assertIn(f"EPOCH={int(t + 100)}", out_b)
        self.assertNotEqual(
            _extract_marker(out_a), _extract_marker(out_b),
            "marker must change when the current song changes")

    def test_marker_stable_when_current_song_unchanged(self):
        # Idempotency: if metadata hasn't changed, the marker value is
        # byte-identical between calls. Otherwise mobile would refresh
        # spuriously on every poll.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "past"), _song(t + 100, "current")]
        out_a = playlist_rewriter.enhance(raw, songs)
        out_b = playlist_rewriter.enhance(raw, songs)
        self.assertEqual(_extract_marker(out_a), _extract_marker(out_b))

    def test_marker_absent_when_no_songs(self):
        # No metadata yet (warmup) → no marker. Playlist passes
        # through unchanged.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        out = playlist_rewriter.enhance(raw, [])
        self.assertNotIn("#EXT-X-RC-METADATA-CHANGED", out)
        self.assertEqual(raw, out)

    def test_marker_absent_when_all_songs_lack_started_at(self):
        # _current_song_started_at filters out started_at <= 0; if
        # everything is invalid, no marker is emitted.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        bad = [{"title": "x", "artist": "y", "started_at": 0}]
        out = playlist_rewriter.enhance(raw, bad)
        self.assertNotIn("#EXT-X-RC-METADATA-CHANGED", out)

    def test_marker_carries_iso8601_with_z_suffix_and_epoch(self):
        # ISO 8601 + Z is unambiguously UTC. The duplicate EPOCH avoids
        # forcing naive parsers to ISO-decode for numeric comparison.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        out = playlist_rewriter.enhance(raw, [_song(t + 42, "x")])
        marker = _extract_marker(out)
        self.assertIsNotNone(marker)
        self.assertIn('STARTED-AT="', marker)
        self.assertIn('Z"', marker)  # UTC marker
        self.assertIn(f"EPOCH={int(t + 42)}", marker)

    def test_marker_present_alongside_daterange(self):
        # When DATERANGE is also being emitted, both must appear in the
        # header block. Order is not contractual but both must be there.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        songs = [_song(t + 5, "past-A"), _song(t + 100, "current-B")]
        out = playlist_rewriter.enhance(raw, songs)
        self.assertIn('X-TITLE="past-A"', out)  # DATERANGE for past
        self.assertIn(f"EPOCH={int(t + 100)}", out)  # marker for current
        # Version still bumped to 6 (DATERANGE requires it).
        self.assertIn("#EXT-X-VERSION:6", out)

    def test_marker_only_no_daterange_does_not_bump_version(self):
        # The custom RC tag has no version requirement (§4.1 unknown
        # tag rule). Bumping to v6 when no DATERANGE is emitted would
        # be a no-op declaration that we support a feature we're not
        # using — keep the source playlist's version.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        self.assertIn("#EXT-X-VERSION:3", raw)
        out = playlist_rewriter.enhance(raw, [_song(t + 5, "current-only")])
        self.assertIn("#EXT-X-VERSION:3", out)
        self.assertNotIn("#EXT-X-VERSION:6", out)

    def test_marker_inserted_in_header_not_between_segments(self):
        # Custom tags before any #EXTINF are header-scoped. Putting the
        # tag mid-playlist could trick a permissive parser into
        # associating it with a specific segment.
        t = 1700000000
        raw = _make_playlist(t, count=5)
        out = playlist_rewriter.enhance(raw, [_song(t + 5, "current")])
        lines = out.split("\n")
        marker_idx = next(i for i, l in enumerate(lines)
                          if "#EXT-X-RC-METADATA-CHANGED" in l)
        first_segment_idx = next(i for i, l in enumerate(lines)
                                 if l.endswith(".ts"))
        self.assertLess(marker_idx, first_segment_idx)


def _extract_marker(playlist: str) -> str | None:
    for line in playlist.split("\n"):
        if line.startswith("#EXT-X-RC-METADATA-CHANGED:"):
            return line
    return None


class TestCurrentSongStartedAt(unittest.TestCase):
    """Pure helper coverage for _current_song_started_at."""

    def test_returns_max_started_at(self):
        songs = [_song(100, "a"), _song(500, "b"), _song(300, "c")]
        self.assertEqual(playlist_rewriter._current_song_started_at(songs), 500)

    def test_returns_none_for_empty(self):
        self.assertIsNone(playlist_rewriter._current_song_started_at([]))

    def test_returns_none_when_all_started_at_invalid(self):
        # started_at == 0 is treated as missing/invalid (the metadata
        # monitor seeds new entries with 0 before the source confirms).
        self.assertIsNone(playlist_rewriter._current_song_started_at(
            [{"started_at": 0}, {"started_at": -1}]
        ))

    def test_ignores_invalid_entries_among_valid_ones(self):
        songs = [{"started_at": 0}, _song(123, "valid"), {"started_at": 0}]
        self.assertEqual(playlist_rewriter._current_song_started_at(songs), 123)

    def test_returns_int_not_float(self):
        # Mobile parses EPOCH as int. Float marker would force the parser
        # to handle "EPOCH=1700000000.5" which we never want to emit.
        self.assertIsInstance(
            playlist_rewriter._current_song_started_at([_song(1.5, "x")]),
            int,
        )


if __name__ == "__main__":
    unittest.main()
