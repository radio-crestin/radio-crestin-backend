"""health_server: /health judges the playlist listeners get (index.m3u8):
deep enough, not behind ffmpeg's live.m3u8, every listed file present.
A stalled metadata monitor is reported without failing /health."""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import health_server as hs  # noqa: E402


def _playlist(uris):
    lines = ["#EXTM3U", "#EXT-X-TARGETDURATION:6", "#EXT-X-MEDIA-SEQUENCE:1"]
    for uri in uris:
        lines += ["#EXTINF:6.000000,",
                  "#EXT-X-PROGRAM-DATE-TIME:2027-01-15T08:00:00.000+0000", uri]
    return "\n".join(lines) + "\n"


class HealthFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(hs, "AAC_SEGMENTS_DIR", str(self.root)),
            mock.patch.object(hs, "FFMPEG_PLAYLIST",
                              str(self.root / "live.m3u8")),
            mock.patch.object(hs, "SERVED_PLAYLIST",
                              str(self.root / "index.m3u8")),
            mock.patch.object(hs, "METADATA_INDEX",
                              str(self.root / "index.json")),
            mock.patch.object(hs, "SEGMENT_HISTORY",
                              str(self.root / "dvr_history.json")),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def segments(self, names, newest_mtime, empty=()):
        """Segment files completed 6 s apart, the last at newest_mtime."""
        for i, name in enumerate(names):
            path = self.root / name
            path.write_bytes(b"" if name in empty else b"\x47")
            mtime = newest_mtime - 6 * (len(names) - 1 - i)
            os.utime(path, (mtime, mtime))

    def playlists(self, live, served):
        (self.root / "live.m3u8").write_text(_playlist(live))
        if served is not None:
            (self.root / "index.m3u8").write_text(_playlist(served))

    def check(self):
        return hs._check_served_playlist()


class ServedPlaylistTests(HealthFixture):
    NAMES = [f"st-1-{i}.ts" for i in range(6)]

    def test_up_to_date_playlist_passes(self):
        self.segments(self.NAMES, time.time() - 2)
        self.playlists(self.NAMES[2:], self.NAMES)
        self.assertEqual(self.check(), (True, ""))

    def test_source_stall_is_not_the_playlists_fault(self):
        # No new segment exists: the newest one is served, however old.
        # (Check 1, segment freshness, judges the stall itself.)
        self.segments(self.NAMES, time.time() - 120)
        self.playlists(self.NAMES[2:], self.NAMES)
        self.assertEqual(self.check(), (True, ""))

    def test_hold_back_within_the_anchor_timeout_passes(self):
        burst = [f"st-2-{i}.ts" for i in range(4)]
        self.segments(self.NAMES, time.time() - 60)
        self.segments(burst, time.time() - 1)
        self.playlists(burst, self.NAMES)
        self.assertEqual(self.check(), (True, ""))

    def test_stuck_rewriter_fails(self):
        # ffmpeg kept producing; the playlist stopped after the 3rd segment,
        # so the 4th has been waiting 36 s (6 segments 6 s apart).
        names = [f"st-1-{i}.ts" for i in range(10)]
        self.segments(names, time.time())
        self.playlists(names, names[:3])
        ok, reason = self.check()
        self.assertFalse(ok)
        self.assertIn("served playlist 36s behind ffmpeg", reason)
        self.playlists(names, names[:5])
        self.assertEqual(self.check(), (True, ""))  # 24 s behind: allowed

    def test_segments_withheld_on_purpose_never_fail(self):
        # A new boot's first segments replay audio the old boot published;
        # the rewriter stamped them and withholds them for good.
        replay = [f"st-2-{i}.ts" for i in range(6)]
        self.segments(self.NAMES, time.time() - 60)
        self.segments(replay, time.time())
        self.playlists(replay, self.NAMES)
        self.assertFalse(self.check()[0])
        (self.root / "dvr_history.json").write_text(json.dumps({
            "version": 3,
            "entries": [{"name": n, "published": True} for n in self.NAMES]
            + [{"name": n, "published": False} for n in replay],
        }))
        self.assertEqual(self.check(), (True, ""))

    def test_missing_or_unpublished_playlist_fails(self):
        self.assertEqual(self.check(), (False, "live.m3u8 not found"))
        self.playlists(self.NAMES, None)
        self.assertEqual(self.check(),
                         (False, "index.m3u8 not found (rewriter has not "
                                 "published)"))

    def test_shallow_playlist_is_warming_up(self):
        self.segments(self.NAMES, time.time())
        self.playlists(self.NAMES, self.NAMES[-(hs.MIN_READY_SEGMENTS - 1):])
        ok, reason = self.check()
        self.assertFalse(ok)
        self.assertIn("warming up", reason)

    def test_listed_segment_missing_or_empty_fails(self):
        self.segments(self.NAMES, time.time())
        self.playlists(self.NAMES, self.NAMES + ["st-1-9.ts"])
        self.assertEqual(self.check(),
                         (False, "1 segments missing from disk (st-1-9.ts)"))
        self.segments(self.NAMES, time.time(), empty={"st-1-3.ts"})
        self.playlists(self.NAMES, self.NAMES)
        self.assertEqual(self.check(),
                         (False, "1 segments are empty (st-1-3.ts)"))


class ServedLagTests(unittest.TestCase):
    MTIMES = {"a": 100.0, "b": 106.0, "c": 112.0, "d": 118.0}

    def lag(self, live, served, now=120.0):
        return hs.served_lag(live, set(served), now, self.MTIMES.get)

    def test_newest_live_segment_served(self):
        self.assertEqual(self.lag(["a", "b", "c"], ["a", "b", "c"]), 0.0)

    def test_lag_is_the_age_of_the_first_unserved_segment(self):
        self.assertEqual(self.lag(["a", "b", "c", "d"], ["a", "b"]), 8.0)

    def test_nothing_served_counts_from_the_first_live_segment(self):
        self.assertEqual(self.lag(["a", "b"], ["x", "y"]), 20.0)

    def test_withheld_replays_do_not_count_once_the_boot_publishes(self):
        # A restarted boot's first segments replay published audio and are
        # never served; the boot's later segments are.
        self.assertEqual(self.lag(["a", "b", "c", "d"], ["c", "d"]), 0.0)

    def test_vanished_files_are_skipped(self):
        self.assertEqual(self.lag(["gone", "c", "d"], ["x"]), 8.0)
        self.assertEqual(self.lag(["gone"], ["x"]), 0.0)

    def test_withheld_segments_count_as_handled(self):
        live = ["a", "b", "c", "d"]
        self.assertEqual(hs.served_lag(live, {"x"}, 120.0, self.MTIMES.get,
                                       frozenset(live)), 0.0)
        # Only what follows the withheld ones is missing.
        self.assertEqual(hs.served_lag(live, {"x"}, 120.0, self.MTIMES.get,
                                       frozenset({"a", "b"})), 8.0)


class WithheldSegmentsTests(unittest.TestCase):
    def test_unpublished_history_entries(self):
        text = json.dumps({"version": 3, "entries": [
            {"name": "a", "published": True},
            {"name": "b", "published": False},
            {"name": "c"},
        ]})
        self.assertEqual(hs.withheld_segments(text), frozenset({"b"}))

    def test_unusable_history_withholds_nothing(self):
        for text in ("", "{", "[]", json.dumps({"entries": [1]})):
            self.assertEqual(hs.withheld_segments(text), frozenset(), text)


class MetadataMonitorTests(HealthFixture):
    def write_alive(self, alive_at):
        (self.root / "index.json").write_text(
            json.dumps({"current": {}, "monitor_alive_at": alive_at}))

    def test_stalled_monitor_is_reported(self):
        self.write_alive(1_000.0)
        self.assertEqual(hs.metadata_monitor_stalled_for(1_075.0), 75.0)

    def test_recent_or_unknown_heartbeat_is_fine(self):
        self.write_alive(1_000.0)
        self.assertIsNone(hs.metadata_monitor_stalled_for(1_030.0))
        self.write_alive(0)
        self.assertIsNone(hs.metadata_monitor_stalled_for(1_030.0))
        (self.root / "index.json").unlink()
        self.assertIsNone(hs.metadata_monitor_stalled_for(1_030.0))

    def test_stalled_monitor_does_not_fail_health(self):
        names = [f"st-1-{i}.ts" for i in range(4)]
        self.segments(names, time.time() - 1)
        self.playlists(names, names)
        self.write_alive(time.time() - 600)
        self.assertEqual(hs.check_health(), (True, ""))


if __name__ == "__main__":
    unittest.main()
