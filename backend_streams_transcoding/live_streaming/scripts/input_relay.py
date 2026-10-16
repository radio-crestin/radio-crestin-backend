"""
Input relay for ffmpeg (FFMPEG_INPUT_RECONNECT=relay): owns the station's
upstream connection and pipes its audio to ffmpeg's stdin, so a reconnect
does not publish the same audio twice.

Icecast and Shoutcast start every connection with a burst of the newest
audio in the mount's queue: 64 KB (4 s) on the Calea Spre Cer mounts, up to
~300 KB (17 s) on others. When a station's source stalls for longer than
ffmpeg's -rw_timeout (10 s), ffmpeg's own in-process reconnect splices that
burst after audio it already encoded, and the HLS output plays it twice
(measured 2026-10-16: 4.075 s twice, 8 times an hour on Biblia and Calea).

The relay keeps the last HISTORY_BYTES it forwarded. A new connection that
starts with the end of that history (every listener of a mount gets the
same queued bytes, so the repeat is exact) has that part dropped, and
ffmpeg reads one continuous stream. When it does not (the source kept going
while the connection was down) the gap is real: everything is forwarded,
as before, and the playlist rewriter dates the gap.

Usage: input_relay.py URL   (audio on stdout, log lines on stderr)

Exit codes: 0 ffmpeg closed the pipe, 1 the upstream stayed unreachable
(ffmpeg then ends and ffmpeg_loop restarts both), 2 usage, 3 the relay
cannot read this upstream but ffmpeg may (a playlist, an ICY status line,
a TLS setup or URL it does not support, on every attempt): it writes
RELAY_UNSUPPORTED_FLAG and the next runs let ffmpeg read the URL itself.
"""

import http.client
import os
import select
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import posthog_reporter
except ImportError:  # posthog missing outside the pod
    posthog_reporter = None

# Like ffmpeg's -rw_timeout: no data for this long ends a connection.
READ_TIMEOUT = float(os.environ.get("RELAY_READ_TIMEOUT", "10"))
# Waits before the 2nd and 3rd attempt after a failed one; the 1st is
# immediate. Then the relay gives up, as ffmpeg does with
# -reconnect_delay_max 4 (it waits 0, 1 and 3 s; the next wait, 7 s, is
# past the max).
RETRY_DELAYS = tuple(float(s) for s in os.environ.get(
    "RELAY_RETRY_DELAYS", "1,3").split(",") if s)
# A connection that gave audio, then went silent for READ_TIMEOUT or
# lasted this long, did not fail: the retries start over, as ffmpeg's do
# after a read. So a source frozen for minutes, whose mount answers every
# reconnect with the same burst, keeps the relay and its history. One that
# ended sooner (a short body, a reset) is a failed attempt: no reconnect
# storm.
STABLE_SECONDS = float(os.environ.get("RELAY_STABLE_SECONDS", "30"))
# Several times the largest connect burst measured (~400 KB).
HISTORY_BYTES = 2 << 20
# The end of the history looked up in a new connection's bytes, placed
# once at least this many have arrived.
ANCHOR_BYTES = 8192
# Overlaps shorter than this are not looked for (at worst this many bytes
# go out twice).
MIN_OVERLAP = 64
# A new connection's bytes are held at most this long while they could
# still be a repeat that has not reached the end of the history: a burst
# arrives within a second, a slow one or a server behind the last one take
# longer. Then they are dropped, and so is what follows while it goes on
# repeating the history.
PLACE_SECONDS = float(os.environ.get("RELAY_PLACE_SECONDS", "15"))
READ_SIZE = 64 * 1024
UNSUPPORTED_EXIT = 3
UNSUPPORTED_FLAG = os.environ.get(
    "RELAY_UNSUPPORTED_FLAG", "/tmp/input_relay_unsupported")
# What ffmpeg sends; some servers answer other clients differently.
USER_AGENT = "Lavf/61.7.100"
# Playlists (HLS, PLS) need ffmpeg's own protocols.
PLAYLIST_TYPES = (
    "application/vnd.apple.mpegurl", "application/x-mpegurl",
    "audio/mpegurl", "audio/x-mpegurl", "audio/x-scpls",
    "application/pls+xml",
)


class ReplayTrimmer:
    """Drops the start of a new connection that repeats audio already
    forwarded (the server's connect burst). Pure: the caller feeds the
    bytes it reads and forwards what comes back.

    A new connection's bytes are held while they could still be a repeat
    that has not reached the end of the history. Then the longest overlap
    with the end of the history is dropped. Digital silence (identical
    frames) also gives shorter ones, and taking one of those would publish
    the rest of the burst again; a longer one can only drop bytes equal to
    the end of the history, more of the same silence."""

    def __init__(self, history_bytes=HISTORY_BYTES,
                 anchor_bytes=ANCHOR_BYTES):
        self._history_bytes = history_bytes
        self._anchor_bytes = anchor_bytes
        self._history = bytearray()
        # A new connection's bytes, while placing them.
        self._held = None
        # Given up holding: the place in the history the incoming bytes
        # repeat, while they do.
        self._replay_at = None
        self.trimmed = 0

    @property
    def holding(self) -> bool:
        """Whether a new connection's bytes are held to place them."""
        return self._held is not None

    @property
    def placing(self) -> bool:
        """Whether the new connection's audio has yet to join the stream:
        its bytes are held, or dropped as a repeat."""
        return self._held is not None or self._replay_at is not None

    def reconnected(self):
        """A new connection starts: place its first bytes in the history."""
        self.trimmed = 0
        self._replay_at = None
        self._held = bytearray() if self._history else None

    def feed(self, data: bytes) -> bytes:
        if self._replay_at is not None:
            return self._drop_replay(data)
        if self._held is None:
            return self._forward(data)
        self._held += data
        return self._place(final=False)

    def connection_ended(self) -> bytes:
        """The connection ended: decide with what it gave."""
        self._replay_at = None
        if self._held is None:
            return b""
        return self._place(final=True)

    def give_up(self) -> bytes:
        """Held PLACE_SECONDS. Bytes that repeat the history short of its
        end (a slow burst, a server behind the last one) are dropped, and so
        is what follows as long as it goes on repeating the history."""
        held = bytes(self._held)
        replay_at = self._repeat_end(held)
        if replay_at is None:
            return self._place(final=True)
        self._held = None
        self.trimmed = len(held)
        self._replay_at = replay_at
        return b""

    def _place(self, final: bool) -> bytes:
        held = self._held
        if len(held) < self._anchor_bytes and not final:
            return b""
        data = bytes(held)
        repeating = self._repeat_end(data) is not None
        if repeating and not final and len(data) < self._history_bytes:
            return b""
        self._held = None
        # Cut off in the middle of a repeat: all it gave repeats.
        self.trimmed = len(data) if repeating else self._overlap(data)
        return self._forward(data[self.trimmed:])

    def _repeat_end(self, data: bytes):
        """Where in the history `data` would go on if it repeats a stretch
        of it short of its end, or None. (A repeat that starts before the
        history would need a burst longer than all the relay forwarded.)"""
        history = self._history
        if len(data) < MIN_OVERLAP:
            return None
        at = history.rfind(data, 0, len(history) - 1)
        return at + len(data) if at >= 0 else None

    def _overlap(self, data: bytes) -> int:
        """The longest L >= MIN_OVERLAP for which `data` starts with the
        last L bytes of the history (or, for L past the history's start,
        has all of it at L - len(history)); 0 if there is none."""
        history = self._history
        n = len(history)
        k = min(self._anchor_bytes, n)
        anchor = bytes(history[n - k:])
        at = data.rfind(anchor)
        while at >= 0:
            length = at + k
            if length <= n:
                found = history[n - length:] == data[:length]
            else:
                found = data[length - n:length] == history
            if found:
                return length
            at = data.rfind(anchor, 0, length - 1)
        # Shorter than the anchor: the history ends with the start of data.
        head = data[:MIN_OVERLAP]
        at = history.find(head, n - k + 1)
        while at >= 0:
            if data.startswith(history[at:]):
                return n - at
            at = history.find(head, at + 1)
        return 0

    def _drop_replay(self, data: bytes) -> bytes:
        """Drops what goes on repeating the history after a give-up."""
        history = memoryview(self._history)
        at = self._replay_at
        same = _common_prefix(history[at:at + len(data)], data)
        history.release()
        self.trimmed += same
        self._replay_at += same
        if same == len(data) and self._replay_at < len(self._history):
            return b""
        # The end of the history reached, or the stream went on differently.
        self._replay_at = None
        return self._forward(data[same:])

    def _forward(self, data: bytes) -> bytes:
        if data:
            self._history += data
            excess = len(self._history) - self._history_bytes
            if excess > 0:
                del self._history[:excess]
        return data


def _common_prefix(a, b) -> int:
    """How many leading bytes `a` and `b` have in common."""
    same, differ = 0, min(len(a), len(b))
    if a[:differ] == b[:differ]:
        return differ
    while differ - same > 1:  # a[:same] == b[:same], a[:differ] differs
        mid = (same + differ) // 2
        if a[:mid] == b[:mid]:
            same = mid
        else:
            differ = mid
    return same


class Unsupported(Exception):
    """An upstream only ffmpeg's own input can read."""


def _log(message: str):
    print(f"input_relay: {message}", file=sys.stderr, flush=True)


def _describe(e: BaseException) -> str:
    if isinstance(e, (socket.timeout, TimeoutError)):
        return f"no data for {READ_TIMEOUT:g} s"
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}"
    return f"{type(e).__name__}: {e}"


def _unsupported_reason(e: BaseException):
    """Why only ffmpeg can read this upstream, or None for an error that
    may pass (no network, a refused or timed out connection, HTTP 5xx)."""
    if isinstance(e, Unsupported):
        return str(e)
    if isinstance(e, http.client.RemoteDisconnected):
        return None
    if isinstance(e, (http.client.BadStatusLine, http.client.UnknownProtocol,
                      http.client.InvalidURL, ValueError)):
        return _describe(e)  # e.g. an "ICY 200 OK" status line, a bad URL
    if isinstance(e, urllib.error.URLError):
        reason = e.reason
        if isinstance(reason, ssl.SSLError) and not isinstance(
                reason, (ssl.SSLZeroReturnError, ssl.SSLEOFError)):
            return f"TLS: {reason}"
        if isinstance(reason, str) and "unknown url type" in reason:
            return reason
    return None


def _open(url: str):
    """The upstream response. Proxies come from the environment (the egress
    sidecar), as for ffmpeg, and like ffmpeg it does not verify
    certificates (some stations' chains are broken) and offers OpenSSL's
    default ciphers, not Python's narrower list."""
    parts = urllib.parse.urlsplit(url)
    if parts.username is not None or parts.password is not None:
        # urllib would take them for the host; ffmpeg sends them.
        raise Unsupported("credentials in the URL")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.set_ciphers("DEFAULT")
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context))
    # No Icy-MetaData: the audio comes without interleaved titles
    # (metadata_monitor reads those over its own connection).
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    response = opener.open(request, timeout=READ_TIMEOUT)
    ctype = (response.headers.get("Content-Type") or "").split(";")[0]
    if ctype.strip().lower() in PLAYLIST_TYPES:
        response.close()
        raise Unsupported(f"a playlist ({ctype})")
    return response


def _kbps(response):
    try:
        return int((response.headers.get("icy-br") or "").split(",")[0])
    except ValueError:
        return None


class Relay:
    def __init__(self, url: str, audio):
        self.url = url
        self.audio = audio
        self.trimmer = ReplayTrimmer()
        self.forwarded = 0
        # When ffmpeg got its last bytes: a reconnect whose burst was all
        # dropped does not end the silence.
        self.audio_at = None

    def run(self) -> int:
        failures = 0  # failed attempts in a row
        unsupported = 0  # of them, the latest in a row only ffmpeg may read
        while True:
            reason = None
            try:
                response = _open(self.url)
            except (OSError, http.client.HTTPException, ValueError,
                    Unsupported) as e:
                if not self.forwarded:
                    reason = _unsupported_reason(e)
                unsupported = unsupported + 1 if reason else 0
                _log(f"connect failed ({_describe(e)})")
            else:
                unsupported = 0
                try:
                    healthy = self._pump(response)
                finally:
                    response.close()
                if healthy:
                    failures = 0
                    continue
            if failures >= len(RETRY_DELAYS):
                # On every attempt, so not a passing glitch.
                if unsupported > failures:
                    return self._unsupported(reason)
                _log(f"upstream unreachable after {failures + 1} attempts, "
                     "giving up")
                return 1
            time.sleep(RETRY_DELAYS[failures])
            failures += 1

    def _pump(self, response) -> bool:
        """Forwards one connection until it ends. Whether it did not fail:
        it gave audio, then went silent or lasted STABLE_SECONDS."""
        reconnect = self.audio_at is not None
        if reconnect:
            self.trimmer.reconnected()
        else:
            _log(f"connected ({response.headers.get('Content-Type')})")
        connected_at = time.monotonic()
        gave_audio = timed_out = False
        # Without audio until this connection's first bytes; reported once
        # they are placed (a connection that gave nothing is not).
        silent_s = None
        reported = not reconnect
        try:
            while True:
                data = response.read1(READ_SIZE)
                if not data:
                    _log("the upstream closed the connection, reconnecting")
                    break
                now = time.monotonic()
                if reconnect and not gave_audio:
                    silent_s = now - self.audio_at
                gave_audio = True
                self._write(self.trimmer.feed(data))
                if self.trimmer.holding and (
                        now - connected_at >= PLACE_SECONDS):
                    self._write(self.trimmer.give_up())
                if not reported and not self.trimmer.placing:
                    reported = True
                    self._report_reconnect(silent_s, response)
        except BrokenPipeError:
            raise
        except (OSError, http.client.HTTPException) as e:
            timed_out = isinstance(e, (socket.timeout, TimeoutError))
            _log(f"{_describe(e)}, reconnecting")
        self._write(self.trimmer.connection_ended())
        if not reported and gave_audio:
            self._report_reconnect(silent_s, response)
        return gave_audio and (
            timed_out or time.monotonic() - connected_at >= STABLE_SECONDS)

    def _write(self, chunk: bytes):
        if chunk:
            self.audio.write(chunk)
            self.audio.flush()
            self.forwarded += len(chunk)
            self.audio_at = time.monotonic()

    def _report_reconnect(self, silent_s: float, response):
        trimmed = self.trimmer.trimmed
        kbps = _kbps(response)
        trimmed_s = (round(trimmed * 8 / (kbps * 1000), 2)
                     if kbps and trimmed else None)
        if trimmed:
            what = f"dropped {trimmed} bytes" + (
                f" ({trimmed_s} s)" if trimmed_s else "") + \
                " the stream already had"
        else:
            what = "nothing repeated"
        _log(f"reconnected after {silent_s:.1f} s without audio, {what}")
        if posthog_reporter is not None:
            posthog_reporter.capture_event("relay_reconnect", {
                "silent_s": round(silent_s, 1),
                "trimmed_bytes": trimmed,
                "trimmed_s": trimmed_s,
            })

    def _unsupported(self, reason: str) -> int:
        _log(f"cannot read this upstream ({reason}); ffmpeg reads it "
             "itself from the next run")
        try:
            with open(UNSUPPORTED_FLAG, "w") as f:
                f.write(reason + "\n")
        except OSError as e:
            _log(f"could not write {UNSUPPORTED_FLAG} ({e})")
        return UNSUPPORTED_EXIT


def _exit_with_ffmpeg(fd: int):
    """Ends the relay as soon as ffmpeg, the pipe's reader, is gone, even
    while the upstream is silent (the next write would only come then)."""
    poller = select.poll()
    poller.register(fd, select.POLLERR | select.POLLHUP)
    poller.poll()
    os._exit(0)


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: input_relay.py URL", file=sys.stderr)
        return 2
    # The audio goes to the original stdout; anything printed (posthog's
    # own lines included) to stderr, never into ffmpeg's input.
    audio = os.fdopen(os.dup(sys.stdout.fileno()), "wb")
    sys.stdout = sys.stderr
    threading.Thread(target=_exit_with_ffmpeg, args=(audio.fileno(),),
                     daemon=True).start()
    try:
        return Relay(argv[1], audio).run()
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    code = main(sys.argv)
    sys.stderr.flush()
    # Skips exit hooks: posthog's final flush could hold up the restart.
    os._exit(code)
