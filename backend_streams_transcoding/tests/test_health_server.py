"""
Regression tests for the live-stream health check.

Reproduces the probe 502s seen on prod: FFmpeg deletes a segment between
glob() and getmtime(), the FileNotFoundError escaped check_health(), and
the probe got no response at all (502 via NGINX). Two in a row restart
the pod through the liveness probe.
"""

import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "live_streaming", "scripts",
))

import health_server  # noqa: E402


@pytest.fixture
def segments_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(health_server, "AAC_SEGMENTS_DIR", tmp)
        monkeypatch.setattr(health_server, "FFMPEG_PLAYLIST", os.path.join(tmp, "live.m3u8"))
        yield tmp


def _write_segments(directory, names):
    for name in names:
        with open(os.path.join(directory, name), "wb") as f:
            f.write(b"\x47" * 188)


def test_segment_deleted_during_check_is_skipped(segments_dir, monkeypatch):
    names = ["s-1.ts", "s-2.ts", "s-3.ts", "s-4.ts"]
    _write_segments(segments_dir, names)
    with open(health_server.FFMPEG_PLAYLIST, "w") as f:
        f.write("#EXTM3U\n" + "\n".join(names[1:]) + "\n")

    real_glob = health_server.glob.glob

    def glob_then_delete_oldest(pattern):
        found = real_glob(pattern)
        os.remove(os.path.join(segments_dir, "s-1.ts"))  # FFmpeg rotates it out
        return found

    monkeypatch.setattr(health_server.glob, "glob", glob_then_delete_oldest)
    assert health_server.check_health() == (True, "")


def test_newest_mtime_ignores_missing_files(segments_dir):
    _write_segments(segments_dir, ["a.ts"])
    present = os.path.join(segments_dir, "a.ts")
    gone = os.path.join(segments_dir, "gone.ts")
    assert health_server._newest_mtime([gone, present]) == os.path.getmtime(present)
    assert health_server._newest_mtime([gone]) == 0.0


def test_stale_segments_still_fail(segments_dir):
    _write_segments(segments_dir, ["a.ts", "b.ts", "c.ts"])
    old = time.time() - health_server.HEALTH_MAX_AGE - 10
    for name in ["a.ts", "b.ts", "c.ts"]:
        os.utime(os.path.join(segments_dir, name), (old, old))
    ok, reason = health_server.check_health()
    assert not ok and "stale" in reason
