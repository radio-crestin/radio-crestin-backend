"""metadata_monitor: song start = detection - delay offset, atomic
index.json, and a reader heartbeat with a watchdog."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "live_streaming", "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import hls_watch  # noqa: E402
import metadata_monitor as mm  # noqa: E402
import playlist_rewriter as pr  # noqa: E402

UPDATE = "[http @ 0x7f8] Metadata update for StreamTitle: {}"


class FakeProc:
    def __init__(self, lines=(), returncode=None):
        self.stderr = [line + "\n" for line in lines]
        self.returncode = returncode
        self.killed = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True


class MonitorFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(mm, "METADATA_DIR", root),
            mock.patch.object(mm, "INDEX_PATH", root / "index.json"),
            mock.patch.object(mm, "STATION_CONFIG_PATH",
                              root / "station.json"),
            mock.patch.object(mm, "_current_song", dict(
                title="", artist="", raw="", started_at=0,
                started_at_iso="")),
            mock.patch.object(mm, "_song_history", []),
            mock.patch.object(mm, "_reader_alive_at", 0.0),
            mock.patch.object(mm, "_current_proc", None),
        ]
        for p in self.patches:
            p.start()
        self.root = root

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def feed(self, lines, now):
        with mock.patch.object(mm.time, "time", return_value=now):
            mm._monitor_ffmpeg_output(FakeProc(lines))

    def index(self):
        return json.loads(mm.INDEX_PATH.read_text())


class SongStartTests(MonitorFixture):
    def test_started_at_is_detection_minus_offset(self):
        mm.STATION_CONFIG_PATH.write_text(json.dumps(
            {"id3_metadata_delay_offset": 10, "config_version": 3}))
        self.feed([UPDATE.format("Artist - Song")], now=1_000.0)
        current = self.index()["current"]
        self.assertEqual(current["raw"], "Artist - Song")
        self.assertEqual(current["started_at"], 990.0)

    def test_negative_offset_dates_later(self):
        mm.STATION_CONFIG_PATH.write_text(json.dumps(
            {"id3_metadata_delay_offset": -10}))
        self.feed([UPDATE.format("Artist - Song")], now=1_000.0)
        self.assertEqual(self.index()["current"]["started_at"], 1_010.0)

    def test_offset_is_zero_without_station_config(self):
        self.feed([UPDATE.format("Artist - Song")], now=1_000.0)
        self.assertEqual(self.index()["current"]["started_at"], 1_000.0)
        mm.STATION_CONFIG_PATH.write_text("{not json")
        self.assertEqual(mm._load_delay_offset(), 0.0)

    def test_reannounced_title_is_not_a_song_change(self):
        # Every (re)connect re-announces the current title; dating it again
        # would invent a boundary (new EPOCH, a DATERANGE for the old one).
        self.feed([UPDATE.format("A - One")], now=1_000.0)
        self.feed(["    StreamTitle     : A - One",
                   UPDATE.format("A - One")], now=1_500.0)
        index = self.index()
        self.assertEqual(index["current"]["started_at"], 1_000.0)
        self.assertEqual(index["recent"], [])
        self.feed([UPDATE.format("B - Two")], now=1_600.0)
        index = self.index()
        self.assertEqual(index["current"]["started_at"], 1_600.0)
        self.assertEqual(index["recent"][0]["ended_at"], 1_600.0)

    def test_progress_and_garbage_lines_are_not_titles(self):
        self.feed(["progress=continue", "out_time_us=6321633",
                   "out_time=00:00:06.321633", "bitrate=N/A",
                   "    StreamTitle     : ChannelElement 3.1 missing",
                   UPDATE.format("")], now=1_000.0)
        self.assertFalse(mm.INDEX_PATH.exists())
        self.assertEqual(mm._current_song["raw"], "")


class HeartbeatTests(MonitorFixture):
    def test_heartbeat_follows_media_time_not_lines(self):
        # ffmpeg keeps printing progress while the source is stalled, with
        # an unchanged out_time (measured on ffmpeg 9): only an advance
        # proves that media arrives.
        stalled = FakeProc(["out_time_us=5000000", "progress=continue",
                            "out_time_us=5000000", "progress=continue"])
        clock = iter([100.0, 200.0])
        with mock.patch.object(mm.time, "time",
                               side_effect=lambda: next(clock)):
            mm._monitor_ffmpeg_output(stalled)
        self.assertEqual(mm._reader_alive_at, 100.0)

        flowing = FakeProc(["out_time_us=1", "out_time_us=2"])
        clock = iter([300.0, 305.0])
        with mock.patch.object(mm.time, "time",
                               side_effect=lambda: next(clock)):
            mm._monitor_ffmpeg_output(flowing)
        self.assertEqual(mm._reader_alive_at, 305.0)

    def test_media_time_parsing(self):
        self.assertEqual(mm.progress_media_time("out_time_us=42"), 42)
        self.assertEqual(mm.progress_media_time("out_time_ms=42"), 42)
        self.assertIsNone(mm.progress_media_time("out_time_us=N/A"))
        self.assertIsNone(mm.progress_media_time("progress=continue"))

    def test_watchdog_kills_a_silent_reader(self):
        proc = FakeProc()
        mm._current_proc = proc
        mm._reader_alive_at = 1_000.0
        self.assertFalse(mm._watchdog_tick(1_000.0 + mm.READER_STALL_TIMEOUT))
        self.assertFalse(proc.killed)
        self.assertTrue(
            mm._watchdog_tick(1_000.0 + mm.READER_STALL_TIMEOUT + 1))
        self.assertTrue(proc.killed)

    def test_watchdog_leaves_an_exited_reader_alone(self):
        proc = FakeProc(returncode=1)
        mm._current_proc = proc
        mm._reader_alive_at = 0.0
        self.assertFalse(mm._watchdog_tick(10_000.0))
        self.assertFalse(proc.killed)

    def test_index_carries_the_heartbeat(self):
        mm._reader_alive_at = 1_234.5
        mm._save_index()
        self.assertEqual(self.index()["monitor_alive_at"], 1_234.5)


class AtomicWriteTests(MonitorFixture):
    def test_index_is_replaced_never_written_in_place(self):
        seen = []
        real_replace = os.replace

        def replace(src, dst):
            # The temp file is complete before it becomes index.json.
            seen.append((Path(dst), json.loads(Path(src).read_text())))
            real_replace(src, dst)

        with mock.patch.object(mm.os, "replace", side_effect=replace):
            mm._save_index()
        self.assertEqual(seen[0][0], mm.INDEX_PATH)
        self.assertIn("current", seen[0][1])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ["index.json"])

    def test_slot_files_are_written_atomically(self):
        with mock.patch.object(mm.os, "replace",
                               wraps=os.replace) as replace:
            self.feed([UPDATE.format("A - One")], now=1_000.0)
            self.feed([UPDATE.format("B - Two")], now=1_200.0)
        targets = [Path(c.args[1]).name for c in replace.call_args_list]
        self.assertIn("00-15.json", targets)  # 1970-01-01 00:16:40


class RecentSongsTests(unittest.TestCase):
    """index.json lists every ended song whose EXT-X-DATERANGE may still map
    to a dvr.m3u8 segment, however many that is."""

    def test_songs_are_kept_by_age_not_by_count(self):
        now = 100_000.0
        # A song every 2 min for 80 min, oldest first.
        history = [{"raw": f"A - {i}", "started_at": now - 120 * (i + 1),
                    "ended_at": now - 120 * i} for i in range(40, 0, -1)]
        recent = mm.recent_songs(history, now)
        self.assertGreater(len(recent), 20)
        self.assertEqual(recent, [s for s in reversed(history)
                                  if s["ended_at"]
                                  > now - mm.RECENT_SONGS_MAX_AGE])
        self.assertEqual(recent[0]["raw"], "A - 1")

    def test_window_outlives_the_rewriters_dvr_trim(self):
        # Both follow DVR_WINDOW_SECONDS; the monitor must keep a song at
        # least as long as the rewriter keeps a segment it overlaps.
        self.assertGreater(mm.RECENT_SONGS_MAX_AGE, pr.DVR_MAX_AGE)


class DvrDaterangeRetentionTests(MonitorFixture):
    """The real monitor, rewriter and canary checker over 75 minutes of a
    station changing songs 30 times an hour: dvr.m3u8 (600 segments, one
    hour) never drops a DATERANGE that still maps to a listed segment."""

    def setUp(self):
        super().setUp()
        segments = self.root / "aac"
        segments.mkdir()
        for name, value in (
                ("SEGMENTS_DIR", segments),
                ("FFMPEG_PLAYLIST", segments / "live.m3u8"),
                ("ENHANCED_PLAYLIST", segments / "index.m3u8"),
                ("DVR_PLAYLIST", segments / "dvr.m3u8"),
                ("DVR_HISTORY_PATH", segments / "dvr_history.json"),
                ("METADATA_PATH", mm.INDEX_PATH),
                ("NOW_PLAYING_PATH", self.root / "now_playing.json")):
            patch = mock.patch.object(pr, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        patch = mock.patch.object(pr.posthog_reporter, "capture_event")
        patch.start()
        self.addCleanup(patch.stop)

    def test_no_daterange_is_removed_while_mapped(self):
        start, song_every = 1_800_000_000.0, 120.0
        checker = hls_watch.PlaylistChecker()
        history = pr._new_history()
        clock = [start]
        names, problems, next_song, song = [], [], start, 0
        with mock.patch.object(mm.time, "time", side_effect=lambda: clock[0]):
            for i in range(750):
                clock[0] = start + 6 * (i + 1)
                while next_song <= clock[0]:
                    song += 1
                    mm._on_title(f"Artist {song} - Song {song}", next_song)
                    next_song += song_every
                mm._save_index()  # the heartbeat
                names.append(self._segment(i, clock[0]))
                live = names[-110:]
                pr._publish(history, self._live(live, len(names) - len(live)),
                            pr._load_songs(), clock[0] + 0.5)
                if pr.DVR_PLAYLIST.exists():  # the boot is anchored
                    problems += checker.feed(pr.DVR_PLAYLIST.read_text(),
                                             None)
        dvr = hls_watch.parse(pr.DVR_PLAYLIST.read_text())
        self.assertEqual(len(dvr.segments), pr.DVR_LIST_SIZE)
        self.assertGreater(len(dvr.dateranges), 20)
        self.assertEqual(problems, [])

    def _segment(self, i, mtime):
        path = pr.SEGMENTS_DIR / f"st-1-{i}.ts"
        path.write_bytes(b"\0")
        os.utime(path, (mtime, mtime))
        return path.name

    @staticmethod
    def _live(names, first_seq):
        lines = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:6",
                 f"#EXT-X-MEDIA-SEQUENCE:{first_seq}"]
        for name in names:
            lines += ["#EXTINF:6.000000,", name]
        return "\n".join(lines) + "\n"


class RestartTests(MonitorFixture):
    """A restarted monitor (supervised restart, or a container restart that
    keeps the data volume) continues the song timeline."""

    def _previous_process(self):
        for i, at in enumerate((1_000.0, 1_120.0, 1_240.0)):
            mm._on_title(f"A - Song {i}", at)
        return self.index()

    def _new_process(self):
        mm._current_song.update(title="", artist="", raw="", started_at=0,
                                started_at_iso="")
        mm._song_history.clear()

    def test_restart_continues_the_timeline(self):
        with mock.patch.object(mm.time, "time", return_value=1_300.0):
            before = self._previous_process()
            self._new_process()
            mm._restore_state()
            mm._save_index()  # the heartbeat's first write
            index = self.index()
            self.assertEqual(index["current"], before["current"])
            self.assertEqual(index["recent"], before["recent"])
            # ffmpeg re-announces the current title when it connects.
            mm._on_title("A - Song 2", 1_330.0)
        index = self.index()
        self.assertEqual(index["current"]["started_at"], 1_240.0)
        self.assertEqual(index["recent"], before["recent"])

    def test_main_restores_before_the_heartbeat_starts(self):
        with mock.patch.object(mm.time, "time", return_value=1_300.0):
            self._previous_process()
        self._new_process()
        current_when_started = []

        def thread(target, daemon):
            current_when_started.append(mm._current_song["raw"])
            return mock.Mock()

        with mock.patch.object(mm, "STREAM_URL", "http://source"), \
                mock.patch.object(mm.threading, "Thread", side_effect=thread), \
                mock.patch.object(mm, "_run_metadata_extractor"):
            mm.main()
        self.assertEqual(current_when_started, ["A - Song 2"] * 2)

    def test_unusable_index_starts_empty(self):
        for text in ("{not json", "[]", json.dumps({"current": 3}),
                     json.dumps({"current": {"raw": "A - B"}})):
            mm.INDEX_PATH.write_text(text)
            mm._restore_state()
            self.assertEqual(mm._current_song["raw"], "", text)
            self.assertEqual(mm._song_history, [], text)


class CommandTests(unittest.TestCase):
    def test_reader_times_out_and_reports_progress(self):
        cmd = mm._ffmpeg_command()
        self.assertEqual(cmd[cmd.index("-rw_timeout") + 1], "10000000")
        self.assertIn("-reconnect_on_network_error", cmd)
        self.assertEqual(cmd[cmd.index("-progress") + 1], "pipe:2")
        self.assertIn("-nostats", cmd)
        self.assertLess(cmd.index("-rw_timeout"), cmd.index("-i"))


if __name__ == "__main__":
    unittest.main()
