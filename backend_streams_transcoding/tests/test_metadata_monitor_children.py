"""
Regression tests for metadata_monitor's FFmpeg child handling.

Reproduces the 2026-10 leak in live-stream-sos-ploiesti: a StreamTitle in
Windows-1250 (not UTF-8) made the strict UTF-8 stderr reader raise, the
retry loop started a new FFmpeg without stopping the old one, and every
reconnect hit the same title again. 50-112 silencedetect FFmpegs piled up
in one burst until the pod was OOM-killed at 384Mi.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import metadata_monitor  # noqa: E402

CP1250_TITLE = "Corul Bisericii - Cântări de laudă şi închinare"


def _fake_ffmpeg(title_bytes: bytes) -> list[str]:
    """A stand-in FFmpeg: prints one StreamTitle line, then keeps streaming."""
    script = (
        "import sys, time\n"
        f"sys.stderr.buffer.write(b'    StreamTitle     : ' + {title_bytes!r} + b'\\n')\n"
        "sys.stderr.flush()\n"
        "time.sleep(60)\n"
    )
    return [sys.executable, "-c", script]


@pytest.fixture(autouse=True)
def metadata_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(metadata_monitor, "METADATA_DIR", Path(tmp))
        monkeypatch.setattr(metadata_monitor, "INDEX_PATH", Path(tmp) / "index.json")
        monkeypatch.setattr(metadata_monitor, "STATION_CONFIG_PATH", Path(tmp) / "station.json")
        monkeypatch.setattr(metadata_monitor, "FFMPEG_STOP_TIMEOUT", 1)
        monkeypatch.setitem(metadata_monitor._current_song, "raw", "")
        yield


@pytest.fixture
def spawned():
    """Every child Popen started, so a test can check none is left running."""
    children = []
    real_popen = subprocess.Popen

    def tracking_popen(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    with mock.patch.object(metadata_monitor.subprocess, "Popen", tracking_popen):
        yield children
    for child in children:
        if child.poll() is None:
            child.kill()
            child.wait()


def _running(children):
    return [c for c in children if c.poll() is None]


class _StopLoop(Exception):
    pass


def _run_retry_loop(fake_cmd, restarts):
    """Run the real retry loop with fake_cmd as FFmpeg, for `restarts` rounds."""
    real_popen = metadata_monitor.subprocess.Popen
    rounds = []

    def fake_sleep(_seconds):
        rounds.append(1)
        if len(rounds) >= restarts:
            raise _StopLoop

    with mock.patch.object(
        metadata_monitor.subprocess, "Popen",
        lambda _cmd, *a, **kw: real_popen(fake_cmd, *a, **kw),
    ), mock.patch.object(
        metadata_monitor, "time", SimpleNamespace(time=time.time, sleep=fake_sleep)
    ):
        with pytest.raises(_StopLoop):
            metadata_monitor._run_metadata_extractor()


class TestNoChildLeak:
    def test_retry_burst_leaves_no_ffmpeg_running(self, spawned):
        # The 2026-10 burst: every reconnect hit the same cp1250 title, the
        # reader raised, and the loop started a new FFmpeg on top of the
        # old one. Now each round's child must be gone before the next.
        bad_title = CP1250_TITLE.encode("cp1250")
        with mock.patch.object(
            metadata_monitor, "_on_song_change", side_effect=RuntimeError("boom")
        ):
            _run_retry_loop(_fake_ffmpeg(bad_title), restarts=5)
        assert len(spawned) == 5
        assert _running(spawned) == []

    def test_parse_error_stops_and_reaps_child(self, spawned):
        cmd = _fake_ffmpeg(b"Artist - Song")
        with mock.patch.object(
            metadata_monitor, "_on_song_change", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError):
                metadata_monitor._run_ffmpeg_once(cmd)
        assert _running(spawned) == []

    def test_cp1250_title_is_parsed_not_raised(self, spawned):
        # The original trigger: Romanian diacritics in Windows-1250.
        cmd = _fake_ffmpeg(CP1250_TITLE.encode("cp1250"))
        with mock.patch.object(
            metadata_monitor, "_on_song_change", side_effect=SystemExit
        ) as on_song_change:
            with pytest.raises(SystemExit):
                metadata_monitor._run_ffmpeg_once(cmd)
        on_song_change.assert_called_once()
        assert on_song_change.call_args.args[0] == CP1250_TITLE
        assert _running(spawned) == []

    def test_child_that_ignores_sigterm_is_killed(self, spawned):
        script = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "sys.stderr.write('    StreamTitle     : Artist - Song\\n')\n"
            "sys.stderr.flush()\n"
            "time.sleep(60)\n"
        )
        with mock.patch.object(
            metadata_monitor, "_on_song_change", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError):
                metadata_monitor._run_ffmpeg_once([sys.executable, "-c", script])
        assert _running(spawned) == []


class TestDecodeLine:
    def test_utf8_kept(self):
        assert metadata_monitor._decode_line("Cântări".encode()) == "Cântări"

    def test_cp1250_fallback(self):
        assert metadata_monitor._decode_line(CP1250_TITLE.encode("cp1250")) == CP1250_TITLE
