"""tools/hls_watch.py: the playlist-contract checker used for the canary."""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import hls_watch as hw  # noqa: E402

T = 1_800_000_000.0


def _pdt(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000+0000", time.gmtime(epoch))


def playlist(first_seq, segments, disc_seq=0, extra=(), start=True):
    """segments: (uri, pdt, discontinuity_before)."""
    lines = ["#EXTM3U", "#EXT-X-VERSION:6", "#EXT-X-TARGETDURATION:6",
             f"#EXT-X-MEDIA-SEQUENCE:{first_seq}",
             f"#EXT-X-DISCONTINUITY-SEQUENCE:{disc_seq}"]
    if start:
        lines.append("#EXT-X-START:TIME-OFFSET=-18")
    lines += list(extra)
    for uri, pdt, disc in segments:
        if disc:
            lines.append("#EXT-X-DISCONTINUITY")
        lines += ["#EXTINF:6.000000,", f"#EXT-X-PROGRAM-DATE-TIME:{_pdt(pdt)}",
                  uri]
    return "\n".join(lines) + "\n"


def run(n, start_pdt, prefix="a", first=100, jump_at=None):
    out, pdt = [], start_pdt
    for i in range(n):
        if jump_at == i:
            pdt += 10
        out.append((f"{prefix}-{first + i}.ts", pdt, False))
        pdt += 6
    return out


class CheckerTests(unittest.TestCase):
    def feed(self, checker, text, last_modified=None):
        return checker.feed(text, last_modified)

    def test_sliding_window_with_restart_and_stall_is_clean(self):
        c = hw.PlaylistChecker()
        segs = run(4, T) + [("b-900.ts", T + 40, True)]
        self.assertEqual(self.feed(c, playlist(10, segs[:4]), T + 24.5), [])
        self.assertEqual(self.feed(c, playlist(10, segs), T + 46.5), [])
        # The window slides past the boot boundary: both sequences advance.
        tail = [(u, p, False) for u, p, _ in segs[4:]]
        self.assertEqual(self.feed(c, playlist(14, tail, disc_seq=1),
                                   T + 46.5), [])
        # A forward PDT jump inside one run is allowed.
        jumpy = run(3, T + 100, prefix="c", jump_at=2)
        self.assertEqual(self.feed(hw.PlaylistChecker(), playlist(1, jumpy)),
                         [])

    def test_changed_segment_and_sequence_going_back(self):
        c = hw.PlaylistChecker()
        segs = run(3, T)
        self.feed(c, playlist(10, segs))
        moved = [(u, p + 1, d) for u, p, d in segs]
        problems = self.feed(c, playlist(9, moved))
        self.assertTrue(any("MEDIA-SEQUENCE went back" in p for p in problems))
        self.assertTrue(any("changed (seq, disc, pdt)" in p
                            for p in problems))

    def test_pdt_overlap(self):
        segs = [("a-1.ts", T, False), ("a-2.ts", T + 3, False)]
        self.assertEqual(self.feed(hw.PlaylistChecker(), playlist(1, segs)),
                         ["PDT overlap a-1.ts -> a-2.ts"])

    def test_daterange_mutation_and_removal_while_mapped(self):
        c = hw.PlaylistChecker()
        segs = run(4, T)
        dr = ('#EXT-X-DATERANGE:ID="song-1",START-DATE="{}",'
              'END-DATE="{}",X-TITLE="{}"')
        a = dr.format(_pdt(T - 30), _pdt(T + 10), "A")
        self.feed(c, playlist(1, segs, extra=[a]))
        self.assertEqual(
            self.feed(c, playlist(1, segs, extra=[a.replace('"A"', '"B"')])),
            ["DATERANGE song-1 attributes changed"])
        self.assertEqual(self.feed(c, playlist(1, segs)),
                         ["DATERANGE song-1 removed while mapped"])

    def test_metadata_changed_hints_may_appear_but_not_change(self):
        c = hw.PlaylistChecker()
        segs = run(3, T)
        tag = '#EXT-X-RC-METADATA-CHANGED:STARTED-AT="x",EPOCH=5'
        self.assertEqual(self.feed(c, playlist(1, segs, extra=[tag])), [])
        hinted = tag + ',X-TITLE="Song, part 2",X-SONG-ID="4"'
        self.assertEqual(self.feed(c, playlist(1, segs, extra=[hinted])), [])
        self.assertEqual(self.feed(c, playlist(1, segs, extra=[tag])), [])
        changed = tag + ',X-TITLE="Other",X-SONG-ID="4"'
        self.assertEqual(self.feed(c, playlist(1, segs, extra=[changed])),
                         ["EPOCH 5 changed X-TITLE"])
        moved = tag.replace('"x"', '"y"')
        self.assertEqual(self.feed(c, playlist(1, segs, extra=[moved])),
                         ["EPOCH 5 changed STARTED-AT"])

    def test_live_edge_lag_is_noted_not_a_violation(self):
        c = hw.PlaylistChecker()
        segs = run(3, T)  # edge ends at T + 18
        self.assertEqual(self.feed(c, playlist(1, segs), T + 19), [])
        self.assertEqual(self.feed(c, playlist(1, segs), T + 30), [])
        self.assertEqual(self.feed(c, playlist(1, segs), T + 14), [])
        self.assertEqual(c.edge_lags, [1.0, 12.0, -4.0])
        self.assertEqual(c.notes, [
            "live edge stale: Last-Modified - edge = 12.0s",
            "PDT ahead of Last-Modified by 4.0s"])

    def test_missing_start_hint(self):
        self.assertEqual(
            self.feed(hw.PlaylistChecker(),
                      playlist(1, run(3, T), start=False)),
            ["no EXT-X-START"])

    def test_attribute_list_keeps_commas_inside_quotes(self):
        attrs = hw.attributes('#X:A="1,2",B=3,C="x"')
        self.assertEqual(attrs, {"A": '"1,2"', "B": "3", "C": '"x"'})


if __name__ == "__main__":
    unittest.main()
