"""
health_server's HTTP probes: /live (liveness) never depends on upstream,
and /health (readiness) answers even when cleanup.sh deletes a segment
between listing and getmtime() (that FileNotFoundError used to escape
check_health(), the probe got a 502 via NGINX).
"""

import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

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
        monkeypatch.setattr(health_server, "SERVED_PLAYLIST", os.path.join(tmp, "index.m3u8"))
        monkeypatch.setattr(health_server, "SEGMENT_HISTORY", os.path.join(tmp, "dvr_history.json"))
        yield tmp


def _write_segments(directory, names):
    for name in names:
        with open(os.path.join(directory, name), "wb") as f:
            f.write(b"\x47" * 188)


def test_segment_deleted_during_check_is_skipped(segments_dir, monkeypatch):
    names = ["s-1.ts", "s-2.ts", "s-3.ts", "s-4.ts"]
    _write_segments(segments_dir, names)
    for playlist in (health_server.FFMPEG_PLAYLIST, health_server.SERVED_PLAYLIST):
        with open(playlist, "w") as f:
            f.write("#EXTM3U\n" + "\n".join(names[1:]) + "\n")

    real_listing = health_server._segment_names

    def list_then_delete(doomed):
        def listing():
            found = real_listing()
            os.remove(os.path.join(segments_dir, doomed))  # cleanup.sh deletes it
            return found
        return listing

    monkeypatch.setattr(health_server, "_segment_names", list_then_delete("s-1.ts"))
    assert health_server.check_health() == (True, "")
    _write_segments(segments_dir, ["s-1.ts"])
    monkeypatch.setattr(health_server, "_segment_names", list_then_delete("s-4.ts"))
    ok, reason = health_server._check_segments_fresh()
    assert ok, reason  # the newest vanished: the next newest is still fresh


def test_newest_segment_is_the_highest_number(segments_dir, monkeypatch):
    # An earlier ffmpeg run (lower boot epoch) and the current one.
    old_run = [f"st-1700000000-{n}.ts" for n in range(1700000000, 1700000005)]
    new_run = [f"st-1700000100-{n}.ts" for n in range(1700000100, 1700000103)]
    _write_segments(segments_dir, old_run + new_run)
    newest = os.path.join(segments_dir, new_run[-1])
    os.utime(newest, (1234.0, 1234.0))

    stat_calls = []
    real_getmtime = os.path.getmtime
    monkeypatch.setattr(health_server.os.path, "getmtime",
                        lambda p: stat_calls.append(p) or real_getmtime(p))
    assert health_server._newest_segment_mtime(health_server._segment_names()) == 1234.0
    assert stat_calls == [newest]


def test_names_without_a_number_check_every_file(segments_dir):
    _write_segments(segments_dir, ["odd.ts", "st-1-5.ts"])
    odd = os.path.join(segments_dir, "odd.ts")
    numbered = os.path.join(segments_dir, "st-1-5.ts")
    os.utime(numbered, (100.0, 100.0))
    os.utime(odd, (200.0, 200.0))
    assert health_server._newest_segment_mtime(health_server._segment_names()) == 200.0


def test_listing_skips_temp_and_hidden_files(segments_dir):
    _write_segments(segments_dir, ["a-1.ts", "a-2.ts.tmp", ".a-3.ts", "live.m3u8"])
    assert health_server._segment_names() == ["a-1.ts"]


def test_missing_directory_has_no_segments(segments_dir, monkeypatch):
    monkeypatch.setattr(health_server, "AAC_SEGMENTS_DIR", os.path.join(segments_dir, "gone"))
    assert health_server._segment_names() == []
    assert health_server.check_health() == (False, "no aac segments on disk")


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


@pytest.fixture
def server(segments_dir):
    httpd = health_server.QuietHTTPServer(("127.0.0.1", 0), health_server.HealthHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_live_answers_while_upstream_is_down(server):
    # No segments at all (station offline): readiness fails, liveness doesn't,
    # so the kubelet leaves the pod alone while ffmpeg_loop reconnects.
    assert _get(server + "/live") == (200, b"alive")
    assert _get(server + "/health") == (503, b"no aac segments on disk")


def test_unknown_path_is_404(server):
    assert _get(server + "/nope")[0] == 404
