"""Wall-clock PDT stamping (wallclock_pdt).

Scenarios mirror what ffmpeg does in production: a connect burst at boot, a
stall followed by an in-process reconnect (with and without a replay burst),
mtime jitter, and an ffmpeg restart whose burst replays audio the previous
boot already published.  Times are relative to an arbitrary epoch T.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import wallclock_pdt as w  # noqa: E402

T = 1_800_000_000.0
D = 6.0


def obs(n, mtime, boot="st-100", duration=D):
    return w.Observation(f"{boot}-{n}.ts", duration, mtime)


def run_boot(observations, now=None, floor=None):
    """Anchor a boot from its first observations, then chain the rest."""
    for k in range(1, len(observations) + 1):
        stamps = w.anchor_new_boot(observations[:k], now or observations[k - 1].mtime + 0.5, floor)
        if stamps:
            break
    else:
        return []
    for o in observations[len(stamps):]:
        stamps.append(w.stamp_next(stamps[-1], o, floor))
    return stamps


class BootAnchorTests(unittest.TestCase):
    def test_burst_segments_are_back_chained_from_first_paced_segment(self):
        # 30 s burst at T: five segments that aired T-30..T, all written
        # within 0.3 s; then real time.
        burst = [obs(i, T + 0.06 * i) for i in range(5)]
        steady = [obs(5 + i, T + 6 * (i + 1)) for i in range(3)]
        stamps = run_boot(burst + steady)
        self.assertAlmostEqual(stamps[0].wall, T - 30, places=6)
        for i, s in enumerate(stamps):
            self.assertAlmostEqual(s.wall, T - 30 + 6 * i, places=6)
        self.assertTrue(all(s.published for s in stamps))

    def test_boot_waits_for_a_paced_segment(self):
        burst = [obs(i, T + 0.06 * i) for i in range(5)]
        self.assertEqual(w.anchor_new_boot(burst, T + 1, None), [])

    def test_boot_falls_back_after_timeout(self):
        burst = [obs(i, T + 0.06 * i) for i in range(5)]
        stamps = w.anchor_new_boot(burst, T + w.BOOT_ANCHOR_TIMEOUT + 1, None)
        self.assertEqual(stamps[-1].wall, burst[-1].mtime - D)
        self.assertEqual(stamps[-1].kind, w.KIND_BOOT_FALLBACK)

    def test_source_without_burst_anchors_on_second_segment(self):
        stamps = run_boot([obs(0, T + 6), obs(1, T + 12), obs(2, T + 18)])
        self.assertAlmostEqual(stamps[0].wall, T, places=6)

    def test_restart_burst_replaying_published_audio_is_not_published(self):
        # Previous boot published audio up to T+290. The new boot starts at
        # T+296 with a 30 s burst (T+266..T+296): its first four segments
        # replay published audio.
        floor = w.BootEnd(pdt=T + 290, audio=T + 290)
        burst = [obs(i, T + 296 + 0.06 * i, boot="st-200") for i in range(5)]
        steady = [obs(5 + i, T + 296 + 6 * (i + 1), boot="st-200") for i in range(2)]
        stamps = run_boot(burst + steady, floor=floor)
        published = [s for s in stamps if s.published]
        self.assertEqual([s.kind for s in stamps[:4]], [w.KIND_DUPLICATE] * 4)
        self.assertGreaterEqual(published[0].wall,
                                floor.pdt - w.OVERLAP_TOLERANCE)
        self.assertAlmostEqual(published[0].wall, T + 290, places=6)
        self.assertFalse(any(s.ahead for s in stamps))


class DriftedBootEndTests(unittest.TestCase):
    """The previous boot ran ahead of the wall clock (audio replayed
    in-process), so its stamps end later than its audio. A new boot must
    withhold only the audio that boot published, and publish the rest at
    once, following its stamps (RFC 8216 6.2.1), instead of freezing the
    live edge until the wall clock passes them."""

    # Stamps end at T+317; the last sample arrived at T+290 (27 s ahead).
    END = w.BootEnd(pdt=T + 317, audio=T + 290)

    def test_only_already_published_audio_is_withheld(self):
        # 30 s connect burst at T+296 (aired T+266..T+296), then real time.
        burst = [obs(i, T + 296 + 0.06 * i, boot="st-200") for i in range(5)]
        steady = [obs(5 + i, T + 296 + 6 * (i + 1), boot="st-200")
                  for i in range(3)]
        stamps = run_boot(burst + steady, floor=self.END)
        aired = [T + 266 + 6 * i for i in range(8)]
        self.assertEqual([s.published for s in stamps],
                         [a >= self.END.audio for a in aired])
        published = [s for s in stamps if s.published]
        self.assertAlmostEqual(published[0].wall, self.END.pdt, places=6)
        for a, b in zip(published, published[1:]):
            self.assertAlmostEqual(b.wall, a.end, places=6)
        self.assertTrue(all(s.ahead for s in published))
        # Reported once, on the anchor, whose residual is the drift.
        self.assertEqual([s.kind for s in published],
                         [w.KIND_BOOT, w.KIND_REPLAY, w.KIND_CHAIN,
                          w.KIND_CHAIN])
        self.assertAlmostEqual(published[1].residual, -27.0, places=6)

    def test_new_audio_after_a_replayed_anchor_follows_the_old_stamps(self):
        # The whole anchored burst replays published audio; the next
        # segment is the boot's first new audio.
        end = w.BootEnd(pdt=T + 330, audio=T + 300)
        burst = [obs(i, T + 296 + 0.06 * i, boot="st-200") for i in range(5)]
        steady = [obs(5 + i, T + 296 + 6 * (i + 1), boot="st-200")
                  for i in range(3)]
        stamps = run_boot(burst + steady, floor=end)
        self.assertEqual([s.published for s in stamps],
                         [False] * 6 + [True] * 2)
        first = stamps[6]
        self.assertAlmostEqual(first.wall, end.pdt, places=6)
        self.assertEqual(first.kind, w.KIND_REPLAY)
        self.assertTrue(first.ahead)
        self.assertAlmostEqual(first.residual, -28.0, places=6)
        self.assertAlmostEqual(stamps[7].wall, first.end, places=6)
        self.assertEqual(stamps[7].kind, w.KIND_CHAIN)

    def test_a_stall_while_replaying_never_publishes_before_the_floor(self):
        # A stall re-anchors the replayed segments' chain; the re-anchored
        # one still aired before the floor, so it stays withheld.
        end = w.BootEnd(pdt=T + 400, audio=T + 400)
        burst = [obs(i, T + 296 + 0.06 * i, boot="st-200") for i in range(5)]
        later = [obs(5, T + 302, boot="st-200"),
                 obs(6, T + 308, boot="st-200"),
                 obs(7, T + 320, boot="st-200"),
                 obs(8, T + 326, boot="st-200")]
        stamps = run_boot(burst + later, floor=end)
        self.assertFalse(any(s.published for s in stamps))

    def test_boot_end_is_where_the_audio_ended(self):
        def last(mtime):
            return w.Stamp("st-100-9.ts", D, mtime, T + 204, True,
                           None if mtime is None else mtime - D - (T + 204),
                           w.KIND_CHAIN)

        self.assertEqual(w.boot_end(last(T + 183)),
                         w.BootEnd(pdt=T + 210, audio=T + 183))
        self.assertEqual(w.boot_end(last(T + 212)),
                         w.BootEnd(pdt=T + 210, audio=T + 210))
        self.assertEqual(w.boot_end(last(None)),
                         w.BootEnd(pdt=T + 210, audio=T + 210))


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.stamps = run_boot([obs(i, T + 6 * (i + 1)) for i in range(4)])

    def follow(self, mtimes):
        for i, m in enumerate(mtimes):
            self.stamps.append(w.stamp_next(self.stamps[-1], obs(100 + i, m)))
        return self.stamps

    def test_jitter_never_moves_the_clock(self):
        last = self.stamps[-1].mtime
        jitter = [0.4, -0.3, 1.5, -1.2, 0.2]
        stamps = self.follow([last + 6 * (i + 1) + j for i, j in enumerate(jitter)])
        for a, b in zip(stamps, stamps[1:]):
            self.assertAlmostEqual(b.wall, a.end, places=6)

    def test_single_late_write_does_not_reanchor(self):
        last = self.stamps[-1].mtime
        stamps = self.follow([last + 6, last + 15, last + 18, last + 24])
        self.assertNotIn(w.KIND_REANCHOR, [s.kind for s in stamps])

    def test_stall_without_burst_reanchors_forward(self):
        # 20 s with no data, then real time again: the audio after the
        # stall aired 20 s later than the chain says.
        last = self.stamps[-1].mtime
        stamps = self.follow([last + 26, last + 32, last + 38])
        self.assertEqual(stamps[-2].kind, w.KIND_REANCHOR)
        self.assertAlmostEqual(stamps[-2].wall, last + 26, places=6)
        self.assertAlmostEqual(stamps[-1].wall, last + 32, places=6)

    def test_stall_with_short_burst_reanchors_by_the_smaller_residual(self):
        last = self.stamps[-1].mtime
        # 20 s stall, 4 s replay burst, then real time.
        stamps = self.follow([last + 20.1, last + 26, last + 32, last + 38])
        reanchored = [s for s in stamps if s.kind == w.KIND_REANCHOR]
        self.assertEqual(len(reanchored), 1)
        self.assertAlmostEqual(stamps[-1].wall, last + 32, places=6)

    def test_replay_burst_never_moves_the_clock_backwards(self):
        # Reconnect after 1 s with a 4 s replay: 3 s of audio repeats. The
        # stamps keep chaining (3 s ahead) instead of overlapping.
        last = self.stamps[-1].mtime
        stamps = self.follow([last + 1.1, last + 4, last + 10, last + 16])
        for a, b in zip(stamps, stamps[1:]):
            self.assertGreaterEqual(b.wall, a.end - 1e-9)

    def test_stamps_never_overlap(self):
        last = self.stamps[-1].mtime
        stamps = self.follow([last + 2, last + 2.1, last + 30, last + 36, last + 37, last + 43])
        for a, b in zip(stamps, stamps[1:]):
            self.assertGreaterEqual(b.wall, a.end - 1e-9)


class BurstTests(unittest.TestCase):
    """A reconnect burst inside a boot is held and dated from the first
    paced segment after it."""

    def setUp(self):
        self.prev = run_boot([obs(i, T + 6 * (i + 1)) for i in range(4)])[-1]
        self.last = self.prev.mtime  # T + 24; prev covers [T + 18, T + 24)

    def test_burst_waits_for_a_paced_segment(self):
        held = [obs(10, self.last + 40), obs(11, self.last + 40.05)]
        self.assertTrue(w.is_burst(held[0], self.last + 39.5))
        self.assertEqual(w.stamp_burst(self.prev, held, self.last + 41), [])

    def test_stall_burst_jumps_forward_at_its_first_segment(self):
        # Audio was lost in a stall; after the reconnect 2 segments arrive
        # as a burst, then real time. Segment 12's audio ended at its mtime
        # (T + 66.05), so segment 10 aired from T + 48.05, 24 s after the
        # chain (T + 24).
        held = [obs(10, self.last + 36.0), obs(11, self.last + 36.05),
                obs(12, self.last + 42.05)]
        stamps = w.stamp_burst(self.prev, held, self.last + 43)
        self.assertEqual([s.kind for s in stamps],
                         [w.KIND_REANCHOR, w.KIND_CHAIN, w.KIND_CHAIN])
        self.assertAlmostEqual(stamps[0].wall, T + 48.05, places=6)
        for a, b in zip(stamps, stamps[1:]):
            self.assertAlmostEqual(b.wall, a.end, places=6)

    def test_replay_burst_keeps_chaining(self):
        # 1 s blip, 5 s replayed: the anchor says the burst started 4 s
        # before the chain; the clock never moves back.
        held = [obs(10, self.last + 1.1), obs(11, self.last + 1.15),
                obs(12, self.last + 7.15)]
        stamps = w.stamp_burst(self.prev, held, self.last + 8)
        # The replay is marked where it was measured: on the paced anchor,
        # whose residual is minus the drift (here 10.85 s replayed).
        self.assertEqual([s.kind for s in stamps],
                         [w.KIND_CHAIN, w.KIND_CHAIN, w.KIND_REPLAY])
        self.assertAlmostEqual(stamps[-1].residual, -10.85, places=6)
        self.assertAlmostEqual(stamps[0].wall, self.prev.end, places=6)

    def test_burst_without_pacing_chains_after_the_timeout(self):
        held = [obs(10, self.last + 0.5), obs(11, self.last + 0.6)]
        now = self.last + 0.5 + w.BOOT_ANCHOR_TIMEOUT + 1
        stamps = w.stamp_burst(self.prev, held, now)
        self.assertEqual(len(stamps), 2)
        self.assertAlmostEqual(stamps[0].wall, self.prev.end, places=6)


class DriftTelemetryTests(unittest.TestCase):
    """Replayed audio leaves the chain ahead of the wall clock; the clock
    cannot move back, so each such episode is reported once (kind replay)
    and tracked by Stamp.ahead until the residual recovers."""

    def setUp(self):
        self.stamps = run_boot([obs(i, T + 6 * (i + 1)) for i in range(4)])
        self.last = self.stamps[-1].mtime  # chain end == T + 24

    def follow(self, mtimes):
        for i, m in enumerate(mtimes):
            self.stamps.append(w.stamp_next(self.stamps[-1], obs(200 + i, m)))
        return self.stamps[-len(mtimes):]

    def test_short_replay_is_reported_once(self):
        # A 1 s blip, then 4 s of audio replayed inside one segment: that
        # segment completes 2 s after its predecessor (still "paced"), and
        # every later segment completes 3.2 s earlier than the chain says
        # (mtime = chain end - 3.2).
        last = self.last
        stamps = self.follow([last + 2, last + 12 - 3.2,
                              last + 18 - 3.2, last + 24 - 3.2])
        self.assertEqual([s.kind for s in stamps],
                         [w.KIND_CHAIN, w.KIND_REPLAY, w.KIND_CHAIN,
                          w.KIND_CHAIN])
        self.assertEqual([s.ahead for s in stamps], [False, True, True, True])
        self.assertAlmostEqual(stamps[1].residual, -3.2, places=6)
        for a, b in zip(stamps, stamps[1:]):
            self.assertAlmostEqual(b.wall, a.end, places=6)

    def test_single_early_write_is_not_an_episode(self):
        stamps = self.follow([self.last + 2, self.last + 12,
                              self.last + 18])
        self.assertNotIn(w.KIND_REPLAY, [s.kind for s in stamps])
        self.assertFalse(any(s.ahead for s in stamps))

    def test_episode_ends_when_the_residual_recovers(self):
        # Ahead by 3 s, then a 5 s stall eats the lead: the residual comes
        # back above the threshold, so a later drift is a new episode.
        last = self.last
        stamps = self.follow([last + 3, last + 9, last + 15,
                              last + 26, last + 32])
        self.assertTrue(stamps[2].ahead)
        self.assertFalse(stamps[3].ahead)
        self.assertEqual([s.kind for s in stamps].count(w.KIND_REPLAY), 1)

    def test_replay_burst_starts_the_episode(self):
        # A replay burst is reported by stamp_burst; the paced segments
        # after it continue the episode without a second report.
        prev = self.stamps[-1]
        held = [obs(10, self.last + 1.1), obs(11, self.last + 1.15),
                obs(12, self.last + 7.15)]
        burst = w.stamp_burst(prev, held, self.last + 8)
        self.assertEqual([s.kind for s in burst].count(w.KIND_REPLAY), 1)
        self.assertEqual(burst[-1].kind, w.KIND_REPLAY)
        self.assertTrue(all(s.ahead for s in burst))
        nxt = w.stamp_next(burst[-1], obs(13, self.last + 13.15))
        self.assertEqual(nxt.kind, w.KIND_CHAIN)
        self.assertTrue(nxt.ahead)

    def test_stall_burst_clears_the_episode(self):
        ahead = self.follow([self.last + 3, self.last + 9,
                             self.last + 15])[-1]
        self.assertTrue(ahead.ahead)
        held = [obs(20, ahead.mtime + 40), obs(21, ahead.mtime + 40.05),
                obs(22, ahead.mtime + 46.05)]
        burst = w.stamp_burst(ahead, held, ahead.mtime + 47)
        self.assertEqual(burst[0].kind, w.KIND_REANCHOR)
        self.assertFalse(any(s.ahead for s in burst))

    def test_new_boot_is_never_ahead(self):
        burst = [obs(i, T + 500 + 0.06 * i, boot="st-300") for i in range(3)]
        steady = [obs(3, T + 506, boot="st-300")]
        stamps = run_boot(burst + steady)
        self.assertFalse(any(s.ahead for s in stamps))


if __name__ == "__main__":
    unittest.main()
