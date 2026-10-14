"""playlist_rewriter publishes wall-clock PDT and keeps it stable.

Runs the real publish step against a temporary segment directory whose file
mtimes play the role of ffmpeg's segment completion times.
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from datetime import datetime
from unittest import mock
from pathlib import Path

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import health_server as hs  # noqa: E402
import playlist_rewriter as pr  # noqa: E402

T = 1_800_000_000.0
# ffmpeg's PDT for these segments: 300 s ahead of the wall clock, as on a
# station whose source bursts on connect.
FFMPEG_SKEW = 300.0


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000+0000", time.gmtime(epoch))


def _pdt_epoch(line):
    return datetime.fromisoformat(
        line.split(":", 1)[1].replace("+0000", "+00:00")).timestamp()


class RewriterFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = {k: getattr(pr, k) for k in (
            "SEGMENTS_DIR", "FFMPEG_PLAYLIST", "ENHANCED_PLAYLIST",
            "DVR_PLAYLIST", "INDEX_2M_PLAYLIST", "INDEX_5M_PLAYLIST",
            "DVR_HISTORY_PATH", "METADATA_PATH")}
        pr.SEGMENTS_DIR = root
        pr.FFMPEG_PLAYLIST = root / "live.m3u8"
        pr.ENHANCED_PLAYLIST = root / "index.m3u8"
        pr.DVR_PLAYLIST = root / "dvr.m3u8"
        pr.INDEX_2M_PLAYLIST = root / "index-2m.m3u8"
        pr.INDEX_5M_PLAYLIST = root / "index-5m.m3u8"
        pr.DVR_HISTORY_PATH = root / "dvr_history.json"
        pr.METADATA_PATH = root / "index.json"
        self.root = root
        self.history = pr._new_history()

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(pr, k, v)
        self.tmp.cleanup()

    def segment(self, boot, n, mtime):
        path = self.root / f"st-{boot}-{n}.ts"
        path.write_bytes(b"\0")
        os.utime(path, (mtime, mtime))
        return path.name

    def live(self, names, first_seq):
        lines = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:6",
                 f"#EXT-X-MEDIA-SEQUENCE:{first_seq}"]
        for i, name in enumerate(names):
            lines += ["#EXTINF:6.000000,",
                      f"#EXT-X-PROGRAM-DATE-TIME:{_iso(T + FFMPEG_SKEW + 6 * i)}",
                      name]
        return "\n".join(lines) + "\n"

    def publish(self, names, first_seq, now, songs=()):
        return pr._publish(self.history, self.live(names, first_seq), list(songs), now)

    def pdts(self, path):
        out, pdt = {}, None
        for line in path.read_text().splitlines():
            if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
                pdt = _pdt_epoch(line)
            elif line.endswith(".ts"):
                out[line] = pdt
        return out


class WallClockPublishTests(RewriterFixture):
    def test_index_carries_wall_clock_not_ffmpeg_pdt(self):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.assertTrue(self.publish(names, 100, T + 25))
        pdts = self.pdts(pr.ENHANCED_PLAYLIST)
        self.assertEqual([pdts[n] for n in names], [T, T + 6, T + 12, T + 18])

    def test_new_boot_is_held_back_until_anchored(self):
        burst = [self.segment(100, i, T + 0.05 * i) for i in range(3)]
        self.assertFalse(self.publish(burst, 100, T + 1))
        self.assertFalse(pr.ENHANCED_PLAYLIST.exists())
        paced = self.segment(100, 3, T + 6)
        self.assertTrue(self.publish(burst + [paced], 100, T + 6.5))
        pdts = self.pdts(pr.ENHANCED_PLAYLIST)
        self.assertEqual(pdts[burst[0]], T - 18)

    def test_published_pdt_never_changes(self):
        names = [self.segment(100, i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        first = self.pdts(pr.ENHANCED_PLAYLIST)
        # Window slides; a stall makes later mtimes jump forward.
        names += [self.segment(100, 4, T + 60), self.segment(100, 5, T + 66)]
        self.publish(names[2:], 102, T + 67)
        second = self.pdts(pr.ENHANCED_PLAYLIST)
        for name in names[2:4]:
            self.assertEqual(first[name], second[name])
        self.assertEqual(second[names[5]], T + 60)  # re-anchored after stall

    def test_history_reload_keeps_stamps(self):
        names = [self.segment(100, i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        before = self.pdts(pr.ENHANCED_PLAYLIST)
        self.history = pr._load_history()
        names.append(self.segment(100, 4, T + 30))
        self.publish(names, 100, T + 31)
        after = self.pdts(pr.ENHANCED_PLAYLIST)
        for name in names[:4]:
            self.assertEqual(before[name], after[name])
        self.assertEqual(after[names[4]], T + 24)

    def test_daterange_cutoff_uses_wall_clock(self):
        names = [self.segment(100, i, T + 6 * (i + 1)) for i in range(4)]
        songs = [
            {"started_at": T - 100, "title": "gone", "artist": "a", "raw": "a - gone"},
            {"started_at": T - 50, "title": "mapped", "artist": "a", "raw": "a - mapped"},
            {"started_at": T + 10, "title": "current", "artist": "a", "raw": "a - current"},
        ]
        self.publish(names, 100, T + 25, songs)
        text = pr.ENHANCED_PLAYLIST.read_text()
        self.assertNotIn('X-TITLE="gone"', text)
        self.assertIn('X-TITLE="mapped"', text)


class RestartContinuityTests(RewriterFixture):
    """Both playlists are windows over one history, so an ffmpeg restart
    appends to them instead of replacing them (RFC 8216 6.2.2)."""

    def _restart(self):
        old = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(old, 100, T + 25)
        new = [self.segment(200, 900 + i, T + 40 + 6 * i) for i in range(3)]
        self.publish(new, 900, T + 53)
        return old, new

    def media(self, path):
        """(uri, media sequence, discontinuity number) per segment."""
        text = path.read_text()
        seq = int(re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", text).group(1))
        disc = int(re.search(r"#EXT-X-DISCONTINUITY-SEQUENCE:(\d+)", text).group(1))
        out = []
        for line in text.splitlines():
            if line == "#EXT-X-DISCONTINUITY":
                disc += 1
            elif line.endswith(".ts"):
                out.append((line, seq, disc))
                seq += 1
        return out

    def test_live_playlist_survives_an_ffmpeg_restart(self):
        old, new = self._restart()
        live = self.media(pr.ENHANCED_PLAYLIST)
        self.assertEqual([u for u, _, _ in live], old + new)
        self.assertEqual([s for _, s, _ in live], list(range(100, 107)))
        # The discontinuity sequence starts like the media sequence (ffmpeg
        # numbers from the epoch), so a replacement pod never repeats one.
        self.assertEqual([d for _, _, d in live], [100] * 4 + [101] * 3)

    def test_sequence_and_discontinuity_numbers_are_stable_when_trimmed(self):
        old, new = self._restart()
        before = {u: (s, d) for u, s, d in self.media(pr.DVR_PLAYLIST)}
        saved = pr.DVR_LIST_SIZE, pr.LIVE_LIST_SIZE
        pr.DVR_LIST_SIZE, pr.LIVE_LIST_SIZE = 2, 2
        try:
            self.publish(new, 900, T + 54)
        finally:
            pr.DVR_LIST_SIZE, pr.LIVE_LIST_SIZE = saved
        for path in (pr.DVR_PLAYLIST, pr.ENHANCED_PLAYLIST):
            after = self.media(path)
            self.assertEqual([u for u, _, _ in after], new[1:])
            for u, s, d in after:
                self.assertEqual(before[u], (s, d))
            self.assertNotIn("#EXT-X-DISCONTINUITY\n", path.read_text())

    def test_trimmed_segments_still_in_live_m3u8_are_not_restamped(self):
        old, _ = self._restart()
        saved = pr.DVR_LIST_SIZE
        pr.DVR_LIST_SIZE = 2
        try:
            self.publish(old, 100, T + 55)
        finally:
            pr.DVR_LIST_SIZE = saved
        names = [e["name"] for e in self.history["entries"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse(set(old) & set(names))

    def test_a_missing_file_drops_the_head_up_to_it(self):
        # Removing only the missing entry would renumber the ones after it.
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(5)]
        self.publish(names, 100, T + 31)
        before = {u: (s, d) for u, s, d in self.media(pr.DVR_PLAYLIST)}
        (self.root / names[2]).unlink()
        self.publish(names[3:], 103, T + 32)
        after = self.media(pr.DVR_PLAYLIST)
        self.assertEqual([u for u, _, _ in after], names[3:])
        for u, s, d in after:
            self.assertEqual(before[u], (s, d))

    def test_entries_expire_by_file_mtime_when_pdt_runs_ahead(self):
        # cleanup.sh deletes by mtime; a PDT running ahead of the files
        # must not keep a segment listed past that.
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        for e in self.history["entries"]:
            e["wall"] += 600
        self.publish(names, 100, T + 6 + pr.DVR_MAX_AGE + 1)
        self.assertNotIn(names[0], pr.DVR_PLAYLIST.read_text())
        self.assertIn(names[1], pr.DVR_PLAYLIST.read_text())

    def test_entries_older_than_the_dvr_age_leave_both_playlists(self):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        self.publish(names, 100, T + pr.DVR_MAX_AGE + 1)
        self.assertNotIn(names[0], pr.DVR_PLAYLIST.read_text())
        self.assertIn(names[1], pr.DVR_PLAYLIST.read_text())

    def test_older_history_format_is_discarded(self):
        name = self.segment(50, 1, T - 100)
        pr.DVR_HISTORY_PATH.write_text(json.dumps([
            {"name": name, "extinf": "#EXTINF:6.000000,",
             "pdt": f"#EXT-X-PROGRAM-DATE-TIME:{_iso(T + 999)}", "seq": 7}
        ]))
        self.history = pr._load_history()
        self.assertEqual(self.history["entries"], [])


class LastModifiedTests(RewriterFixture):
    """nginx serves the playlists' mtime as Last-Modified; clients compare
    it with the live edge's PDT, so a playlist is only rewritten when its
    bytes change (not on every index.json heartbeat)."""

    OLD = 1_000_000_000.0  # any time before a real write

    def _playlists(self):
        return (pr.ENHANCED_PLAYLIST, pr.DVR_PLAYLIST, pr.INDEX_2M_PLAYLIST,
                pr.INDEX_5M_PLAYLIST)

    def _age_playlists(self):
        for path in self._playlists():
            os.utime(path, (self.OLD, self.OLD))

    def test_identical_render_keeps_the_mtime(self):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        songs = [{"started_at": T + 3, "raw": "a - b", "title": "b",
                  "artist": "a"}]
        self.publish(names, 100, T + 25, songs)
        self._age_playlists()
        self.publish(names, 100, T + 26, songs)
        for path in self._playlists():
            self.assertEqual(path.stat().st_mtime, self.OLD)

    def test_new_segment_or_metadata_rewrites(self):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        self._age_playlists()
        names.append(self.segment(100, 104, T + 30))
        self.publish(names, 100, T + 31)
        self.assertGreater(pr.ENHANCED_PLAYLIST.stat().st_mtime, self.OLD)
        self._age_playlists()
        songs = [{"started_at": T + 29, "raw": "a - b", "title": "b",
                  "artist": "a"}]
        self.publish(names, 100, T + 32, songs)
        self.assertGreater(pr.ENHANCED_PLAYLIST.stat().st_mtime, self.OLD)
        self.assertIn("EPOCH=", pr.ENHANCED_PLAYLIST.read_text())


class RenderedHeaderTests(RewriterFixture):
    def test_inserted_tags_follow_the_discontinuity_sequence(self):
        # EXT-X-DISCONTINUITY-SEQUENCE is a header tag; the injected tags
        # must not split the header before it.
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        songs = [{"started_at": T + 3, "raw": "a - b", "title": "b",
                  "artist": "a"}]
        self.publish(names, 100, T + 25, songs)
        lines = pr.ENHANCED_PLAYLIST.read_text().splitlines()
        disc_seq = next(i for i, l in enumerate(lines)
                        if l.startswith("#EXT-X-DISCONTINUITY-SEQUENCE:"))
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("#EXT-X-START:"))
        first_extinf = next(i for i, l in enumerate(lines)
                            if l.startswith("#EXTINF:"))
        self.assertLess(disc_seq, start)
        self.assertLess(start, first_extinf)


class DriftPersistenceTests(RewriterFixture):
    def test_ahead_survives_a_history_reload(self):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(names, 100, T + 25)
        # Two segments 3 s early: the chain is confirmed ahead.
        names += [self.segment(100, 104, T + 27), self.segment(100, 105, T + 33)]
        self.publish(names, 100, T + 34)
        entries = self.history["entries"]
        self.assertEqual(entries[-1]["kind"], "replay")
        self.assertTrue(entries[-1]["ahead"])
        self.history = pr._load_history()
        self.assertTrue(pr._stamp_of(self.history["entries"][-1]).ahead)
        names.append(self.segment(100, 106, T + 39))
        self.publish(names, 100, T + 40)
        self.assertEqual(self.history["entries"][-1]["kind"], "chain")
        self.assertTrue(self.history["entries"][-1]["ahead"])


class DriftedRestartTests(RewriterFixture):
    """ffmpeg restarts after an in-process reconnect replayed 30 s of audio
    (stage 1): the replay is withheld except for 3 s, so the old boot's
    stamps end 3 s after its audio. The new boot's audio after that point
    is new and must reach listeners at once; withholding it froze the live
    edge until /health failed."""

    def _drifted_boot(self):
        """Boot 100: 20 paced segments, a 1 s blip whose reconnect burst
        replays 30 s, then 10 paced segments. Returns its last mtime."""
        names = []
        for i in range(20):
            names.append(self.segment(100, i, T + 6 * (i + 1)))
            self.publish(names[-110:], 0, T + 6 * (i + 1) + 0.5)
        t = T + 123
        names += [self.segment(100, 20 + j, t + 0.01 * j) for j in range(5)]
        self.publish(names[-110:], 0, t + 0.1)
        for j in range(10):
            t += 6
            names.append(self.segment(100, 25 + j, t))
            self.publish(names[-110:], 0, t + 0.5)
        return t

    def test_replayed_audio_is_withheld_after_a_discontinuity(self):
        audio_end = self._drifted_boot()
        last = pr._published(self.history["entries"])[-1]
        # Only the first burst segment (3 s new audio, 3 s replay) chains;
        # the 24 s of replayed audio after it are withheld.
        self.assertAlmostEqual(last["wall"] + 6 - audio_end, 3.0, places=3)
        withheld = [e["name"] for e in self.history["entries"]
                    if not e["published"]]
        self.assertEqual(withheld, [f"st-100-{n}.ts" for n in range(21, 25)])
        text = pr.DVR_PLAYLIST.read_text()
        self.assertEqual(text.count("#EXT-X-DISCONTINUITY\n"), 1)
        uris = hs.playlist_uris(text)
        self.assertEqual(uris[uris.index("st-100-20.ts") + 1], "st-100-25.ts")
        pdts = list(self.pdts(pr.DVR_PLAYLIST).values())
        for a, b in zip(pdts, pdts[1:]):
            self.assertGreaterEqual(b - a, 6 - 1e-3)

    def test_new_audio_is_published_at_once_and_health_stays_up(self):
        audio_end = self._drifted_boot()
        last = pr._published(self.history["entries"])[-1]
        pdt_end = last["wall"] + 6
        self.assertAlmostEqual(pdt_end - audio_end, 3.0, places=3)
        # The new boot connects 2 s later: 30 s burst, then real time.
        start = audio_end + 2
        names = [self.segment(200, j, start + 0.01 * j) for j in range(5)]
        lags = []
        for step in range(40):
            now = start + 0.1 + step
            if step and step % 6 == 0:
                names.append(self.segment(200, len(names), start + step))
            self.publish(names, 0, now)
            served = set(hs.playlist_uris(pr.ENHANCED_PLAYLIST.read_text()))
            withheld = hs.withheld_segments(pr.DVR_HISTORY_PATH.read_text())
            lags.append(hs.served_lag(names, served, now, self._mtime,
                                      withheld))
        self.assertLess(max(lags), hs.HEALTH_MAX_AGE)
        # Segment j of the new boot aired at start - 30 + 6 j: only what
        # aired before the old boot's audio ended is withheld.
        entries = {e["name"]: e for e in self.history["entries"]}
        for j, name in enumerate(names):
            aired = start - 30 + 6 * j
            self.assertEqual(entries[name]["published"],
                             aired >= audio_end, name)
        # PDT continues where the old stamps end; it never goes back.
        pdts = list(self.pdts(pr.ENHANCED_PLAYLIST).values())
        self.assertEqual(pdts, sorted(pdts))
        first_new = next(e for e in self.history["entries"]
                         if e["name"].startswith("st-200-")
                         and e["published"])
        self.assertAlmostEqual(first_new["wall"], pdt_end, places=3)
        # 2 s between the runs leave 1 s of drift: below REANCHOR_THRESHOLD.
        self.assertEqual(first_new["kind"], "boot")
        self.assertFalse(first_new["ahead"])

    def _mtime(self, uri):
        try:
            return (self.root / uri).stat().st_mtime
        except OSError:
            return None


class PersistBeforePublishTests(RewriterFixture):
    """A stamp in a playlist is already on disk, so a rewriter killed
    between the two writes never re-dates a published segment."""

    def _boot(self):
        """Pod start: a 30 s connect burst, then the first paced segment."""
        return ([self.segment(100, i, T + 0.01 * i) for i in range(5)]
                + [self.segment(100, 5, T + 6)])

    def _fail_writes_to(self, target):
        real = pr.write_atomic

        def write_atomic(path, content):
            if path == target:
                raise OSError("killed")
            real(path, content)

        return mock.patch.object(pr, "write_atomic", write_atomic)

    def test_nothing_is_published_before_its_stamp_is_persisted(self):
        names = self._boot()
        with self._fail_writes_to(pr.DVR_HISTORY_PATH):
            with self.assertRaises(OSError):
                self.publish(names, 0, T + 6.5)
        self.assertFalse(pr.ENHANCED_PLAYLIST.exists())
        self.assertEqual(self.history["entries"], [])

    def test_a_restart_after_a_failed_playlist_write_keeps_the_stamps(self):
        names = self._boot()
        with self._fail_writes_to(pr.ENHANCED_PLAYLIST):
            with self.assertRaises(OSError):
                self.publish(names, 0, T + 6.5)
        persisted = {e["name"]: e["wall"]
                     for e in pr._load_history()["entries"]}
        self.assertEqual(set(persisted), set(names))
        # Restarted 2 s later; the source stalled 3 s after segment 5, so
        # anchoring the boot again would date it 3 s later.
        names += [self.segment(100, 6, T + 15), self.segment(100, 7, T + 21)]
        self.history = pr._load_history()
        self.publish(names, 0, T + 21.5)
        pdts = self.pdts(pr.ENHANCED_PLAYLIST)
        for name, wall in persisted.items():
            self.assertAlmostEqual(pdts[name], wall, places=3)

    def test_a_failed_history_write_is_retried_before_publishing(self):
        names = self._boot()
        with self._fail_writes_to(pr.DVR_HISTORY_PATH):
            with self.assertRaises(OSError):
                self.publish(names, 0, T + 6.5)
        self.publish(names, 0, T + 7.5)
        on_disk = {e["name"]: e["wall"]
                   for e in pr._load_history()["entries"]}
        pdts = self.pdts(pr.ENHANCED_PLAYLIST)
        self.assertEqual(set(pdts), set(on_disk))
        for name, wall in on_disk.items():
            self.assertAlmostEqual(pdts[name], wall, places=3)


class ErrorReportTests(unittest.TestCase):
    def setUp(self):
        self.reported = []
        self.saved = (pr.posthog_reporter.capture_exception,
                      pr._last_error_report)
        pr.posthog_reporter.capture_exception = (
            lambda e, context=None: self.reported.append(str(e)))
        pr._last_error_report = ("", 0.0)

    def tearDown(self):
        pr.posthog_reporter.capture_exception, pr._last_error_report = (
            self.saved)

    def test_a_repeating_error_is_reported_once_per_interval(self):
        for t in range(0, 30):
            pr._report_error(OSError("disk full"), T + t)
        pr._report_error(ValueError("other"), T + 31)
        pr._report_error(OSError("disk full"),
                         T + pr.ERROR_REPORT_INTERVAL + 1)
        self.assertEqual(self.reported, ["disk full", "other", "disk full"])


class StartOffsetTests(unittest.TestCase):
    def test_start_offset_is_three_target_durations(self):
        raw = "#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6.0,\nseg.ts\n"
        self.assertIn("#EXT-X-START:TIME-OFFSET=-18", pr.enhance(raw, []))
        raw = raw.replace("TARGETDURATION:6", "TARGETDURATION:7")
        self.assertIn("#EXT-X-START:TIME-OFFSET=-21", pr.enhance(raw, []))


class TargetDurationTests(RewriterFixture):
    """EXT-X-TARGETDURATION covers every EXTINF either playlist ever listed
    (RFC 8216 4.3.3.1) and never decreases; ffmpeg's value only covers its
    own window."""

    def publish_extinfs(self, extinfs, now):
        names = [self.segment(100, 100 + i, T + 6 * (i + 1))
                 for i in range(len(extinfs))]
        lines = ["#EXTM3U", "#EXT-X-TARGETDURATION:6",
                 "#EXT-X-MEDIA-SEQUENCE:100"]
        for name, extinf in zip(names, extinfs):
            lines += [f"#EXTINF:{extinf},", name]
        pr._publish(self.history, "\n".join(lines) + "\n", [], now)

    def target(self, path):
        return int(re.search(r"#EXT-X-TARGETDURATION:(\d+)",
                             path.read_text()).group(1))

    def test_rounds_to_the_nearest_second(self):
        self.publish_extinfs(["6.040000"] * 4, T + 25)
        self.assertEqual(self.target(pr.DVR_PLAYLIST), 6)

    def test_covers_the_longest_segment_and_never_decreases(self):
        self.publish_extinfs(["6.000000", "7.400000", "6.000000",
                              "6.000000"], T + 25)
        for path in (pr.ENHANCED_PLAYLIST, pr.DVR_PLAYLIST):
            self.assertEqual(self.target(path), 7)
            self.assertIn("#EXT-X-START:TIME-OFFSET=-21", path.read_text())
        saved = pr.DVR_LIST_SIZE
        pr.DVR_LIST_SIZE = 2
        try:
            self.publish_extinfs(["6.000000", "7.400000", "6.000000",
                                  "6.000000"], T + 26)
        finally:
            pr.DVR_LIST_SIZE = saved
        self.assertNotIn("st-100-101.ts", pr.DVR_PLAYLIST.read_text())
        self.assertEqual(self.target(pr.DVR_PLAYLIST), 7)
        self.assertEqual(pr._load_history()["target_duration"], 7)


class LongOutageTests(RewriterFixture):
    """ffmpeg's last live.m3u8 stays on disk through an outage. Once all of
    it has expired from history it must not be stamped again (a PostHog
    event and a history write every second), and no playlist may keep
    listing segments cleanup.sh deletes."""

    def test_expired_segments_are_never_restamped(self):
        events = []
        names = [self.segment(100, 100 + i, T - 6 * (109 - i))
                 for i in range(110)]
        self.publish(names, 100, T + 1)
        playlists = (pr.ENHANCED_PLAYLIST, pr.DVR_PLAYLIST,
                     pr.INDEX_2M_PLAYLIST, pr.INDEX_5M_PLAYLIST)
        for path in playlists:
            self.assertTrue(path.exists(), path.name)
        with mock.patch.object(pr.posthog_reporter, "capture_event",
                               lambda *a, **k: events.append(a)):
            for later in (3905, 3906, 4000):
                self.assertTrue(self.publish(names, 100, T + later))
            self.history = pr._load_history()
            self.assertTrue(self.publish(names, 100, T + 4001))
        self.assertEqual(events, [])
        self.assertEqual(self.history["entries"], [])
        for path in playlists:
            self.assertFalse(path.exists(), path.name)

    def test_the_next_boot_is_published_after_the_outage(self):
        old = [self.segment(100, 100 + i, T + 6 * (i + 1)) for i in range(4)]
        self.publish(old, 100, T + 25)
        self.publish(old, 100, T + 25 + pr.DVR_MAX_AGE + 60)
        start = T + 30 + pr.DVR_MAX_AGE + 60
        new = [self.segment(200, 900 + i, start + 6 * i) for i in range(3)]
        self.publish(new, 900, start + 13)
        self.assertEqual(hs.playlist_uris(pr.ENHANCED_PLAYLIST.read_text()),
                         new)


class OffsetVariantPublishTests(RewriterFixture):
    """index-2m.m3u8 / index-5m.m3u8 are rendered from the exact index.m3u8
    text of the same pass, after index.m3u8 and dvr.m3u8, and never at
    their expense: every client that does not ask for a variant (old app
    versions, the web player) keeps getting exactly those two."""

    SONGS = [
        {"started_at": T + 3, "raw": "a - b", "title": "b", "artist": "a"},
        {"started_at": T + 200, "raw": "a - c", "title": "c", "artist": "a"},
    ]
    DEFAULT_START = "#EXT-X-START:TIME-OFFSET=-18\n"

    def _segments(self, count=70):
        """`count` paced segments of boot 100: a 420 s window, room for
        both offsets."""
        return [self.segment(100, 100 + i, T + 6 * (i + 1))
                for i in range(count)]

    def _publish_all(self, names):
        self.assertTrue(self.publish(names, 100, T + 6 * len(names) + 1,
                                     self.SONGS))

    def _variant_of(self, index, offset):
        self.assertIn(self.DEFAULT_START, index)
        return index.replace(self.DEFAULT_START,
                             f"#EXT-X-START:TIME-OFFSET=-{offset}\n")

    def test_variants_are_index_with_a_deeper_start(self):
        self._publish_all(self._segments())
        index = pr.ENHANCED_PLAYLIST.read_text()
        self.assertEqual(pr.INDEX_2M_PLAYLIST.read_text(),
                         self._variant_of(index, 120))
        self.assertEqual(pr.INDEX_5M_PLAYLIST.read_text(),
                         self._variant_of(index, 300))

    def test_index_and_dvr_are_the_same_as_without_variants(self):
        names = self._segments()
        with mock.patch.object(pr, "_publish_offset_variants"):
            self._publish_all(names)
        self.assertFalse(pr.INDEX_2M_PLAYLIST.exists())
        before = {path: path.read_text()
                  for path in (pr.ENHANCED_PLAYLIST, pr.DVR_PLAYLIST)}
        for path in (*before, pr.DVR_HISTORY_PATH):
            path.unlink()
        self.history = pr._new_history()
        self._publish_all(names)
        for path, text in before.items():
            self.assertEqual(path.read_text(), text, path.name)

    def test_variants_are_written_after_index_and_dvr(self):
        written = []
        real = pr.write_atomic

        def write_atomic(path, content):
            written.append(path.name)
            real(path, content)

        with mock.patch.object(pr, "write_atomic", write_atomic):
            self._publish_all(self._segments())
        self.assertEqual(written, ["dvr_history.json", "index.m3u8",
                                   "dvr.m3u8", "index-2m.m3u8",
                                   "index-5m.m3u8"])

    def test_a_failing_variant_never_holds_back_index_and_dvr(self):
        names = self._segments()
        self._publish_all(names)
        names.append(self.segment(100, 100 + len(names),
                                  T + 6 * (len(names) + 1)))
        real = pr._offset_variant
        reported = []

        def offset_variant(index, offset):
            if offset == pr.INDEX_2M_OFFSET:
                raise RuntimeError("variant bug")
            return real(index, offset)

        with mock.patch.object(pr, "_offset_variant", offset_variant), \
                mock.patch.object(pr, "_last_error_report", ("", 0.0)), \
                mock.patch.object(pr.posthog_reporter, "capture_exception",
                                  lambda e, context=None:
                                  reported.append(str(e))):
            self._publish_all(names)
        self.assertEqual(reported, ["variant bug"])
        index = pr.ENHANCED_PLAYLIST.read_text()
        self.assertIn(names[-1], index)
        self.assertIn(names[-1], pr.DVR_PLAYLIST.read_text())
        self.assertEqual(pr.INDEX_5M_PLAYLIST.read_text(),
                         self._variant_of(index, 300))
        # A stale copy would stop advancing under its listeners; without
        # the file nginx answers 404 and apps fall back to index.m3u8.
        self.assertFalse(pr.INDEX_2M_PLAYLIST.exists())
        # The next pass brings it back.
        self.assertTrue(self.publish(names, 100, T + 6 * len(names) + 2,
                                     self.SONGS))
        self.assertEqual(pr.INDEX_2M_PLAYLIST.read_text(),
                         self._variant_of(index, 120))


if __name__ == "__main__":
    unittest.main()
