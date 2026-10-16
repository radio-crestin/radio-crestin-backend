"""input_relay: on a reconnect, the new connection's burst of audio the
stream already had is dropped, so ffmpeg reads one continuous stream; when
nothing repeats (a network stall) everything is forwarded. Unit tests of
ReplayTrimmer, then the real script against a local server that bursts on
connect like Icecast."""

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "live_streaming" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import input_relay as ir  # noqa: E402

# Non-repeating bytes: a big-endian 32-bit counter, so every window of a
# few bytes occurs once.
PATTERN = b"".join(i.to_bytes(4, "big") for i in range(1 << 20))


def span(start, length):
    return PATTERN[start:start + length]


class ReplayTrimmerTests(unittest.TestCase):
    def setUp(self):
        self.t = ir.ReplayTrimmer(history_bytes=64 * 1024, anchor_bytes=1024)

    def forward(self, data):
        self.assertEqual(self.t.feed(data), data)

    def reconnect_with(self, data, chunk=None):
        self.t.reconnected()
        if chunk is None:
            return self.t.feed(data)
        return b"".join(self.t.feed(data[i:i + chunk])
                        for i in range(0, len(data), chunk))

    def test_first_connection_passes_through(self):
        self.forward(span(0, 5000))
        self.assertFalse(self.t.placing)

    def test_burst_of_audio_already_forwarded_is_dropped(self):
        self.forward(span(0, 20_000))
        # Icecast's burst: the newest 4000 bytes of its queue, which the
        # stream already had (the source stalled), then new audio.
        out = self.reconnect_with(span(16_000, 4000) + span(20_000, 3000))
        self.assertEqual(out, span(20_000, 3000))
        self.assertEqual(self.t.trimmed, 4000)
        self.assertFalse(self.t.placing)
        self.forward(span(23_000, 500))

    def test_burst_arriving_in_small_reads(self):
        self.forward(span(0, 20_000))
        out = self.reconnect_with(span(15_000, 5000) + span(20_000, 2000),
                                  chunk=700)
        self.assertEqual(out, span(20_000, 2000))

    def test_partial_replay_keeps_the_new_audio(self):
        self.forward(span(0, 20_000))
        # The source resumed during the reconnect: the burst goes 2500 bytes
        # past what the stream had.
        out = self.reconnect_with(span(18_500, 4000))
        self.assertEqual(out, span(20_000, 2500))

    def test_burst_starting_within_the_last_anchor(self):
        self.forward(span(0, 20_000))
        # Only 300 bytes repeat, fewer than the 1024-byte anchor.
        out = self.reconnect_with(span(19_700, 3000))
        self.assertEqual(out, span(20_000, 2700))
        self.assertEqual(self.t.trimmed, 300)

    def test_nothing_repeated_forwards_at_once(self):
        self.forward(span(0, 20_000))
        # The source kept going: the queue moved past what the stream had.
        out = self.reconnect_with(span(30_000, 10_000))
        self.assertEqual(out, span(30_000, 10_000))
        self.assertEqual(self.t.trimmed, 0)

    def test_connection_cut_in_the_middle_of_the_burst(self):
        self.forward(span(0, 20_000))
        # 2500 bytes of an 8000-byte repeat, then the connection drops: all
        # of it repeats, none goes out, and the next one is placed alike.
        self.assertEqual(self.reconnect_with(span(12_000, 2500)), b"")
        self.assertEqual(self.t.connection_ended(), b"")
        out = self.reconnect_with(span(12_000, 8000) + span(20_000, 1000))
        self.assertEqual(out, span(20_000, 1000))

    def test_connection_ending_before_the_anchor_is_in(self):
        self.forward(span(0, 20_000))
        self.assertEqual(self.reconnect_with(span(40_000, 500)), b"")
        self.assertEqual(self.t.connection_ended(), span(40_000, 500))

    def test_a_match_far_back_that_goes_on_differently_is_no_repeat(self):
        # A jingle aired again 10 s later, byte for byte, then other audio:
        # the start matches the history, the rest does not.
        jingle = span(500_000, 3000)
        self.forward(span(0, 4000) + jingle + span(10_000, 20_000))
        new = jingle + span(70_000, 4000)
        out = self.reconnect_with(new)
        self.assertEqual(out, new)
        self.assertEqual(self.t.trimmed, 0)

    def test_a_slow_burst_is_dropped_after_the_give_up(self):
        # The burst is still coming when the relay gives up holding it
        # (after PLACE_SECONDS): what repeats is dropped as it comes.
        self.forward(span(0, 20_000))
        self.assertEqual(self.reconnect_with(span(10_000, 4000)), b"")
        self.assertTrue(self.t.holding)
        self.assertEqual(self.t.give_up(), b"")
        self.assertFalse(self.t.holding)
        self.assertTrue(self.t.placing)
        self.assertEqual(self.t.feed(span(14_000, 5000)), b"")
        self.assertEqual(self.t.feed(span(19_000, 1500)), span(20_000, 500))
        self.assertFalse(self.t.placing)
        self.assertEqual(self.t.trimmed, 10_000)
        self.forward(span(20_500, 100))

    def test_given_up_while_matching_older_audio(self):
        # The same spot again, byte for byte, for longer than the hold:
        # dropped until the stream goes on differently.
        older = span(300_000, 6000)
        self.forward(older + span(10_000, 20_000))
        self.assertEqual(self.reconnect_with(older[:5000]), b"")
        self.assertEqual(self.t.give_up(), b"")
        # (Mid-word, so that no byte of the counter happens to match.)
        self.assertEqual(self.t.feed(older[5000:5500] + span(80_002, 100)),
                         span(80_002, 100))
        self.assertEqual(self.t.trimmed, 5500)
        self.forward(span(80_102, 100))

    def test_digital_silence_takes_the_longest_overlap(self):
        # Identical frames: the burst also lines up with the end of the
        # history shifted by whole frames. The longest overlap is the
        # burst; at worst a longer one would drop more of the silence.
        frame = span(900_000, 256)
        self.forward(span(0, 4000) + frame * 16)
        new = span(50_000, 3000)
        self.assertEqual(self.reconnect_with(frame * 16 + new), new)
        self.assertEqual(self.t.trimmed, 16 * 256)

    def test_silence_at_both_ends_of_the_burst(self):
        # The burst starts in a pause and the history ends in one: their
        # silent frames also make short overlaps, but the burst repeats the
        # speech between them too.
        frame = span(900_000, 256)
        speech = span(100_000, 6000)
        self.forward(span(0, 8000) + frame * 8 + speech + frame * 8)
        burst = frame * 3 + speech + frame * 8
        new = span(60_000, 2000)
        self.assertEqual(self.reconnect_with(burst + new, chunk=700), new)
        self.assertEqual(self.t.trimmed, len(burst))

    def test_a_burst_starting_in_long_silence(self):
        # The burst's start occurs a hundred times in the history.
        frame = span(900_000, 256)
        speech = span(100_000, 3000)
        self.forward(span(0, 2000) + frame * 100 + speech)
        burst = frame * 60 + speech
        new = span(60_000, 2000)
        self.assertEqual(self.reconnect_with(burst + new), new)
        self.assertEqual(self.t.trimmed, len(burst))

    def test_history_is_bounded(self):
        for i in range(0, 200_000, 10_000):
            self.forward(span(i, 10_000))
        self.assertEqual(len(self.t._history), 64 * 1024)
        out = self.reconnect_with(span(190_000, 10_000) + span(200_000, 100))
        self.assertEqual(out, span(200_000, 100))


class Source:
    """A station's source and its server: audio produced at a steady rate,
    each new listener first gets a burst of the newest queued bytes."""

    def __init__(self, rate=64_000, burst=16_000, ctype="audio/mpeg",
                 chunked=False, body_limit=None, status_line=None,
                 status_lines=None):
        self.rate, self.burst, self.ctype = rate, burst, ctype
        self.chunked = chunked
        self.body_limit = body_limit
        # Sent instead of a response, to the first `status_lines`
        # connections (all when None).
        self.status_line = status_line
        self.status_lines = status_lines
        self.produced = 0
        self.connections = 0
        self.paused_until = 0.0
        self.silent_until = 0.0  # the server sends nothing (network)
        self.cond = threading.Condition()
        self.running = True
        threading.Thread(target=self._produce, daemon=True).start()
        source = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1" if chunked else "HTTP/1.0"

            def log_message(self, *a):
                pass

            def do_GET(self):
                source.serve(self)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/radio.mp3"

    def _produce(self):
        step = 0.02
        while self.running:
            time.sleep(step)
            with self.cond:
                if time.monotonic() >= self.paused_until:
                    self.produced += int(self.rate * step)
                    self.cond.notify_all()

    def serve(self, handler):
        self.connections += 1
        if self.status_line and (self.status_lines is None
                                 or self.connections <= self.status_lines):
            handler.wfile.write(self.status_line + b"\r\n\r\n")
            return
        handler.send_response(200)
        handler.send_header("Content-Type", self.ctype)
        if self.chunked:
            handler.send_header("Transfer-Encoding", "chunked")
        handler.end_headers()
        if self.ctype.startswith("application/"):
            return
        with self.cond:
            pos = max(0, self.produced - self.burst)
        sent = 0
        try:
            while self.running:
                with self.cond:
                    while self.produced <= pos and self.running:
                        self.cond.wait(0.1)
                    end = self.produced
                if time.monotonic() < self.silent_until:
                    time.sleep(0.05)
                    continue
                data = span(pos, end - pos)
                if self.body_limit is not None:
                    data = data[:self.body_limit - sent]
                if self.chunked:
                    handler.wfile.write(b"%x\r\n%s\r\n" % (len(data), data))
                else:
                    handler.wfile.write(data)
                handler.wfile.flush()
                pos = end
                sent += len(data)
                if self.body_limit is not None and sent >= self.body_limit:
                    return
        except OSError:
            pass

    def close(self):
        self.running = False
        self.server.shutdown()
        self.server.server_close()


class RelayProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flag = os.path.join(self.tmp.name, "unsupported")
        self.env = {
            k: v for k, v in os.environ.items()
            if k.lower() not in ("http_proxy", "https_proxy", "no_proxy")}
        self.env.update(RELAY_READ_TIMEOUT="1", RELAY_RETRY_DELAYS="0.2,0.4",
                        RELAY_STABLE_SECONDS="1.5",
                        RELAY_UNSUPPORTED_FLAG=self.flag)

    def start(self, url, stdout=None):
        if stdout is None:
            stdout = open(os.path.join(self.tmp.name, "out"), "wb")
            self.addCleanup(stdout.close)
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS / "input_relay.py"), url],
            stdout=stdout, stderr=subprocess.PIPE, env=self.env)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        return proc

    def output(self):
        with open(os.path.join(self.tmp.name, "out"), "rb") as f:
            return f.read()

    def assert_contiguous(self, data):
        start = PATTERN.find(data[:64])
        self.assertGreaterEqual(start, 0)
        self.assertEqual(data, span(start, len(data)),
                         "the relay's output repeats or skips bytes")

    def wait_for(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        self.fail("timed out")

    def stop(self, proc):
        proc.terminate()
        proc.wait(5)
        return proc.stderr.read().decode()

    def run_source_stall(self, **source_args):
        src = Source(**source_args)
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.wait_for(lambda: len(self.output()) > 100_000)
        # The source stalls longer than the read timeout: the relay
        # reconnects and gets the burst of what it already forwarded.
        src.paused_until = time.monotonic() + 1.8
        time.sleep(4)
        log = self.stop(proc)
        self.assertIn("dropped 16000 bytes the stream already had", log)
        self.assert_contiguous(self.output())
        return log

    def test_source_stall_reconnects_without_a_repeat(self):
        log = self.run_source_stall()
        self.assertRegex(log, r"reconnected after 1\.\d s without audio")

    def test_chunked_upstream(self):
        self.run_source_stall(chunked=True)

    def test_a_long_freeze_keeps_the_relay(self):
        # The mount stays up: every reconnect gets the same burst, then
        # nothing. Each such connection gave audio, so none is a failure.
        src = Source()
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.wait_for(lambda: len(self.output()) > 100_000)
        src.paused_until = time.monotonic() + 5
        time.sleep(6.5)
        self.assertIsNone(proc.poll())
        log = self.stop(proc)
        self.assertNotIn("giving up", log)
        self.assertGreaterEqual(log.count("dropped 16000 bytes"), 3)
        self.assert_contiguous(self.output())

    def test_a_long_stall_is_reported_whole(self):
        src = Source()
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.wait_for(lambda: len(self.output()) > 100_000)
        # Two reconnects during one stall, each burst all dropped: the
        # second still counts from the last audio ffmpeg got.
        src.paused_until = time.monotonic() + 2.6
        time.sleep(4.5)
        log = self.stop(proc)
        self.assertRegex(log, r"reconnected after 1\.\d s without audio")
        self.assertRegex(log, r"reconnected after 2\.\d s without audio")
        self.assert_contiguous(self.output())

    def test_printed_lines_stay_out_of_the_audio(self):
        # posthog_reporter prints a line when first used, at the first
        # reconnect ("enabled" in the pod; here, with a key but no posthog
        # package, "not installed"): it must go to stderr, not into ffmpeg.
        self.env.update(POSTHOG_API_KEY="test",
                        POSTHOG_HOST="http://127.0.0.1:9")
        log = self.run_source_stall()
        self.assertIn("posthog_reporter:", log)

    def test_network_stall_forwards_the_gap(self):
        src = Source()
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.wait_for(lambda: len(self.output()) > 100_000)
        # The server stops sending while the source keeps going: the burst
        # holds nothing the relay had, so it all goes to ffmpeg.
        src.silent_until = time.monotonic() + 1.5
        time.sleep(4)
        self.assertIn("nothing repeated", self.stop(proc))
        data = self.output()
        # Two contiguous runs: before the drop and after the reconnect.
        first = PATTERN.find(data[:64])
        n = 0
        while data[n:n + 4] == span(first + n, 4):
            n += 4
        self.assertGreater(n, 100_000)
        self.assert_contiguous(data[n:])
        self.assertGreater(PATTERN.find(data[n:n + 64]), first + n)

    def test_short_bodies_do_not_cause_a_reconnect_storm(self):
        # 200 with a short body every time (an error page, a static file).
        src = Source(body_limit=2000)
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.assertEqual(proc.wait(10), 1)
        self.assertEqual(src.connections, 3)
        self.assertIn("giving up", proc.stderr.read().decode())

    def test_playlist_upstream_is_left_to_ffmpeg(self):
        src = Source(ctype="application/vnd.apple.mpegurl")
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.assertEqual(proc.wait(10), ir.UNSUPPORTED_EXIT)
        with open(self.flag) as f:
            self.assertIn("mpegurl", f.read())

    def test_credentials_in_the_url_are_left_to_ffmpeg(self):
        proc = self.start("http://user:secret@127.0.0.1:9/radio.mp3")
        self.assertEqual(proc.wait(10), ir.UNSUPPORTED_EXIT)
        with open(self.flag) as f:
            self.assertIn("credentials", f.read())

    def test_icy_status_line_is_left_to_ffmpeg(self):
        src = Source(status_line=b"ICY 200 OK\r\nicy-name: test")
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.assertEqual(proc.wait(10), ir.UNSUPPORTED_EXIT)
        self.assertTrue(os.path.exists(self.flag))

    def test_a_single_unreadable_answer_is_not_a_fallback(self):
        src = Source(status_line=b"ICY 200 OK\r\nicy-name: test",
                     status_lines=1)
        self.addCleanup(src.close)
        proc = self.start(src.url)
        self.wait_for(lambda: len(self.output()) > 20_000)
        self.assertIsNone(proc.poll())
        self.assertFalse(os.path.exists(self.flag))
        self.stop(proc)

    def test_gives_up_when_the_upstream_stays_down(self):
        with socket.socket() as s:  # a port nothing listens on
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        proc = self.start(f"http://127.0.0.1:{port}/radio.mp3")
        started = time.monotonic()
        self.assertEqual(proc.wait(10), 1)
        # Immediate first attempt, then 0.2 and 0.4 s.
        self.assertLess(time.monotonic() - started, 5)
        self.assertIn("giving up", proc.stderr.read().decode())
        self.assertFalse(os.path.exists(self.flag))

    def test_exits_as_soon_as_ffmpeg_is_gone(self):
        src = Source()
        self.addCleanup(src.close)
        proc = self.start(src.url, stdout=subprocess.PIPE)
        proc.stdout.read(10_000)
        # Even while the upstream sends nothing, so no write would fail.
        src.paused_until = time.monotonic() + 30
        time.sleep(0.5)
        proc.stdout.close()
        started = time.monotonic()
        self.assertEqual(proc.wait(10), 0)
        self.assertLess(time.monotonic() - started, 0.9)


if __name__ == "__main__":
    unittest.main()
