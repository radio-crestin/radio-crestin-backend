"""metadata_monitor with STREAM_SINGLE_INPUT: titles and the heartbeat come
from input_relay.py over a unix socket, silences from the transcoder's
SILENCE_LOG, and no FFmpeg of the monitor's own runs until the relay leaves
a fallback flag. A relay title is dated exactly as the same title read by
the monitor's own FFmpeg at the same instant."""

import json
import os
import shutil
import socket
import tempfile
import threading
import time
from unittest import mock

from tests.test_metadata_monitor import UPDATE, MonitorFixture, mm


class SingleInputFixture(MonitorFixture):
    def setUp(self):
        super().setUp()
        # AF_UNIX paths are short on macOS: not under TMPDIR.
        self.sock_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(shutil.rmtree, self.sock_dir)
        self.flags = (os.path.join(self.tmp.name, "unsupported"),
                      os.path.join(self.tmp.name, "no_titles"))
        self.silence_log = os.path.join(self.tmp.name, "silence.log")
        for p in (
            mock.patch.object(mm, "EVENTS_SOCKET",
                              os.path.join(self.sock_dir, "m.sock")),
            mock.patch.object(mm, "RELAY_FALLBACK_FLAGS", self.flags),
            mock.patch.object(mm, "SILENCE_LOG", self.silence_log),
        ):
            p.start()
            self.addCleanup(p.stop)

    def relay_state(self, title=None, title_at=None, audio_at=None):
        mm._reader_alive_at = mm.on_relay_state(
            {"title": title, "title_at": title_at, "audio_at": audio_at},
            mm._reader_alive_at)


class RelayTitleTests(SingleInputFixture):
    def test_dated_like_the_monitors_own_reader(self):
        mm.STATION_CONFIG_PATH.write_text(json.dumps(
            {"id3_metadata_delay_offset": 10}))
        self.relay_state("Artist - Song", 1_000.0, 1_000.0)
        from_relay = self.index()["current"]
        self.setUp()  # a fresh monitor, the same title read by FFmpeg
        mm.STATION_CONFIG_PATH.write_text(json.dumps(
            {"id3_metadata_delay_offset": 10}))
        self.feed([UPDATE.format("Artist - Song")], now=1_000.0)
        self.assertEqual(from_relay, self.index()["current"])
        self.assertEqual(from_relay["started_at"], 990.0)

    def test_heartbeats_repeating_the_title_are_not_song_changes(self):
        t0 = time.time() - 60  # "recent" keeps songs by age
        self.relay_state("A - One", t0, t0)
        for t in (t0 + 5, t0 + 10, t0 + 15):
            self.relay_state("A - One", t0, t)
        self.assertEqual(self.index()["recent"], [])
        self.relay_state("B - Two", t0 + 20, t0 + 20)
        index = self.index()
        self.assertEqual(index["current"]["started_at"], t0 + 20)
        self.assertEqual(index["recent"][0]["started_at"], t0)
        self.assertEqual(index["recent"][0]["ended_at"], t0 + 20)

    def test_heartbeat_is_when_audio_last_flowed(self):
        self.relay_state(audio_at=1_000.0)
        self.assertEqual(mm._reader_alive_at, 1_000.0)
        # A late or title-only message never moves it back.
        self.relay_state(audio_at=990.0)
        self.relay_state("A - One", 1_001.0)
        self.assertEqual(mm._reader_alive_at, 1_000.0)

    def test_non_titles_are_ignored(self):
        for raw in ("", "-", "n/a",
                    "[aac @ 0x55d5c8a3e2c0] ChannelElement 3.1 missing"):
            self.relay_state(raw, 1_000.0, 1_000.0)
        self.assertFalse(mm.INDEX_PATH.exists())
        self.relay_state("Corul - Cântări şi laudă", 1_000.0, 1_000.0)
        self.assertEqual(self.index()["current"]["raw"],
                         "Corul - Cântări şi laudă")


class SilenceLogTests(SingleInputFixture):
    def test_new_starts_once_each(self):
        log = mm.SilenceLog(self.silence_log)
        self.assertEqual(log.new_starts(), [])  # no file yet
        with open(self.silence_log, "w") as f:
            f.write("frame:10 pts:1 pts_time:1.5\n"
                    "lavfi.silence_start=1.25\n"
                    "frame:90 pts:9 pts_time:9.5\nlavfi.silence_st")
        self.assertEqual(log.new_starts(), [1.25])
        with open(self.silence_log, "a") as f:
            f.write("art=9.1\n")
        self.assertEqual(log.new_starts(), [9.1])
        self.assertEqual(log.new_starts(), [])

    def test_a_new_transcoder_run_starts_the_file_over(self):
        log = mm.SilenceLog(self.silence_log)
        with open(self.silence_log, "w") as f:
            f.write("lavfi.silence_start=1\n" * 50)
        self.assertEqual(len(log.new_starts()), 50)
        with open(self.silence_log, "w") as f:
            f.write("lavfi.silence_start=2\n")
        self.assertEqual(log.new_starts(), [2.0])


class ListenerTests(SingleInputFixture):
    def send(self, state):
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.sendto(json.dumps(state).encode(), mm.EVENTS_SOCKET)

    def wait_for(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail("timed out")

    def test_listens_without_ffmpeg_until_the_relay_falls_back(self):
        sock = mm._relay_socket()
        self.addCleanup(sock.close)
        result = []
        with mock.patch.object(mm.subprocess, "Popen",
                               side_effect=AssertionError("ffmpeg started")):
            thread = threading.Thread(
                target=lambda: result.append(mm._listen_to_relay(sock)),
                daemon=True)
            thread.start()
            now = time.time()
            self.send({"title": "A - One", "title_at": now, "audio_at": now})
            self.wait_for(lambda: mm._current_song["raw"] == "A - One")
            self.assertEqual(mm._reader_alive_at, now)
            with mock.patch.object(mm, "_on_silence") as on_silence:
                with open(self.silence_log, "w") as f:
                    f.write("lavfi.silence_start=4.5\n")
                self.wait_for(lambda: on_silence.called)
            with open(self.flags[1], "w") as f:
                f.write("no icy-metaint header\n")
            thread.join(5)
        self.assertEqual(result, ["no icy-metaint header"])

    def test_garbage_datagrams_are_ignored(self):
        sock = mm._relay_socket()
        self.addCleanup(sock.close)
        thread = threading.Thread(target=mm._listen_to_relay, args=(sock,),
                                  daemon=True)
        thread.start()
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.sendto(b"\xff not json", mm.EVENTS_SOCKET)
            s.sendto(b"[1, 2]", mm.EVENTS_SOCKET)
        now = time.time()
        self.send({"title": "A - One", "title_at": now, "audio_at": now})
        self.wait_for(lambda: mm._current_song["raw"] == "A - One")
        open(self.flags[0], "w").close()  # an empty flag still counts
        thread.join(5)
        self.assertFalse(thread.is_alive())


class MainTests(SingleInputFixture):
    def run_main(self, single_input):
        calls = []
        with mock.patch.object(mm, "SINGLE_INPUT", single_input), \
                mock.patch.object(mm, "STREAM_URL", "http://station"), \
                mock.patch.object(mm, "signal"), \
                mock.patch.object(mm.threading, "Thread"), \
                mock.patch.object(mm, "_run_single_input",
                                  lambda: calls.append("single")), \
                mock.patch.object(mm, "_run_metadata_extractor",
                                  lambda: calls.append("ffmpeg")):
            mm.main()
        return calls

    def test_single_input_falls_back_to_the_monitors_own_reader(self):
        self.assertEqual(self.run_main(True), ["single", "ffmpeg"])

    def test_without_the_flag_nothing_changes(self):
        self.assertEqual(self.run_main(False), ["ffmpeg"])

    def test_needs_the_relay(self):
        on = {"STREAM_SINGLE_INPUT": "1", "FFMPEG_INPUT_RECONNECT": "relay"}
        self.assertTrue(mm.single_input_enabled(on))
        self.assertFalse(mm.single_input_enabled(
            {**on, "FFMPEG_INPUT_RECONNECT": "inprocess"}))
        self.assertFalse(mm.single_input_enabled(
            {**on, "STREAM_SINGLE_INPUT": "0"}))
        self.assertFalse(mm.single_input_enabled({}))
