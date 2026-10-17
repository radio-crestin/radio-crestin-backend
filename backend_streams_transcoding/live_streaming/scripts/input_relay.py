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

With STREAM_SINGLE_INPUT=1 the relay is also the pod's only reader of the
station's titles: it asks for ICY metadata (Icy-MetaData: 1), takes the
metadata blocks out of the audio (ffmpeg and the history see exactly the
audio they did without them) and sends metadata_monitor each StreamTitle,
with when it was read, over a unix datagram socket. When it cannot (no
icy-metaint header, a block that is not ICY metadata, a server that answers
the request in a way only ffmpeg reads) it writes RELAY_NO_TITLES_FLAG,
goes on without metadata, and metadata_monitor reads the titles over its
own connection, as without the flag.

Usage: input_relay.py URL   (audio on stdout, log lines on stderr)

An unreachable upstream (a refused or silent connection, HTTP 404 while
the station's encoder reconnects to its server) is retried for as long as
it lasts, a few seconds apart at most, and so is an unexpected error: ffmpeg
waits on the pipe and its run goes on, one continuous stream, when the
station is back. (The relay used to give up after 3 attempts: ffmpeg then
ended, and the restart, with its backoff of up to 20 s and a new run in the
playlist, came on top of the outage.)

Exit codes: 0 ffmpeg closed the pipe, 2 usage, 3 the relay cannot read this
upstream but ffmpeg may (a playlist, an ICY status line, a TLS setup or URL
it does not support, on its first UNSUPPORTED_ATTEMPTS attempts): it writes
RELAY_UNSUPPORTED_FLAG and the next runs let ffmpeg read the URL itself.
"""

import http.client
import json
import os
import re
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
# Waits after the 1st, 2nd, ... failed attempt in a row; the last one
# repeats for as long as the upstream stays down, so the stream is back at
# most that long after the station. The 1st attempt after a connection
# that ended is immediate.
RETRY_DELAYS = tuple(float(s) for s in os.environ.get(
    "RELAY_RETRY_DELAYS", "0.5,1,2").split(",") if s)
# Only an upstream unreadable on this many attempts in a row, before any
# audio, is left to ffmpeg (a single odd answer is not).
UNSUPPORTED_ATTEMPTS = 3
# Failed attempts logged one by one; then one line a minute while the
# upstream stays down.
LOGGED_FAILURES = 3
QUIET_LOG_SECONDS = 60
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
# STREAM_SINGLE_INPUT: the titles come over the relay's connection.
SINGLE_INPUT = os.environ.get("STREAM_SINGLE_INPUT") == "1"
# metadata_monitor's socket, and the flag that sends it back to its own
# connection for the container's life.
MONITOR_SOCKET = os.environ.get(
    "METADATA_EVENTS_SOCKET", "/tmp/metadata_monitor.sock")
NO_TITLES_FLAG = os.environ.get(
    "RELAY_NO_TITLES_FLAG", "/tmp/input_relay_no_titles")
# The monitor hears the stream's state at least this often while audio
# flows (its stall check, and a restarted monitor learns the title).
HEARTBEAT_SECONDS = 5.0
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


_ICY_FIELD = re.compile(rb"(\w+)='(.*?)';(?=\w+='|\s*$)", re.S)
_ICY_START = re.compile(rb"[A-Za-z]\w*='")


def parse_icy_metadata(block: bytes):
    """The fields of one ICY metadata block ({b"StreamTitle": b"..."}),
    or None when the block is not ICY metadata (the stream is out of
    step). Values may hold quotes; a field ends at "';" before the next
    field or the end."""
    text = block.rstrip(b"\0")
    if not text:
        return {}
    if b"\0" in text or not _ICY_START.match(text):
        return None
    fields = {key: value for key, value in _ICY_FIELD.findall(text)}
    return fields or None


def decode_title(raw: bytes) -> str:
    """Stations send titles in UTF-8 or Windows-1250 (ş, ţ: many Romanian
    ones), as metadata_monitor decodes ffmpeg's lines."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1250", errors="replace")


class IcyDemuxer:
    """Splits an ICY stream into its audio and its metadata blocks. Pure.

    After every `metaint` bytes of audio comes one length byte (x16 bytes)
    and that much metadata; 0 means none. Reads split anywhere. A block
    that is not metadata means the stream is out of step: `out_of_step`
    says why, and the rest of that read is left out (what comes after it
    can no longer be told apart)."""

    def __init__(self, metaint: int):
        self.metaint = metaint
        self._audio_left = metaint
        # Bytes of the current metadata block still to come, while in one.
        self._meta_left = None
        self._meta = bytearray()
        self.out_of_step = None

    def feed(self, data: bytes):
        """(audio, [metadata fields]) in `data`."""
        audio = bytearray()
        blocks = []
        view = memoryview(data)
        while view and self.out_of_step is None:
            if self._meta_left is None and self._audio_left:
                n = min(self._audio_left, len(view))
                audio += view[:n]
                self._audio_left -= n
                view = view[n:]
            elif self._meta_left is None:
                self._meta_left = view[0] * 16
                view = view[1:]
                self._end_block_if_done(blocks)
            else:
                n = min(self._meta_left, len(view))
                self._meta += view[:n]
                self._meta_left -= n
                view = view[n:]
                self._end_block_if_done(blocks)
        view.release()
        return bytes(audio), blocks

    def _end_block_if_done(self, blocks):
        if self._meta_left:
            return
        if self._meta:
            fields = parse_icy_metadata(bytes(self._meta))
            if fields is None:
                self.out_of_step = (
                    f"a {len(self._meta)}-byte metadata block that is not "
                    f"ICY metadata ({bytes(self._meta[:24])!r})")
                return
            blocks.append(fields)
        self._meta = bytearray()
        self._meta_left = None
        self._audio_left = self.metaint


class MonitorChannel:
    """Tells metadata_monitor the stream's state: the latest title, when it
    was read, and when audio last went to ffmpeg. Best effort: while the
    monitor is not listening a message is lost, and the next one (at least
    every HEARTBEAT_SECONDS while audio flows) carries the same state."""

    def __init__(self, path: str = MONITOR_SOCKET):
        self.path = path
        self.title = None
        self.title_at = None
        self.audio_at = None
        self._sent_at = 0.0
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._socket.setblocking(False)

    def title_read(self, title: str, at: float):
        if title != self.title:
            self.title, self.title_at = title, at
            self.send()

    def audio_sent(self, at: float):
        self.audio_at = at
        if at - self._sent_at >= HEARTBEAT_SECONDS:
            self.send()

    def send(self):
        self._sent_at = time.time()
        message = json.dumps({"title": self.title, "title_at": self.title_at,
                              "audio_at": self.audio_at}).encode()
        try:
            self._socket.sendto(message, self.path)
        except OSError:
            pass  # no monitor yet, or busy: the next heartbeat repeats it


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


def _open(url: str, icy: bool = False):
    """The upstream response. Proxies come from the environment (the egress
    sidecar), as for ffmpeg, and like ffmpeg it does not verify
    certificates (some stations' chains are broken) and offers OpenSSL's
    default ciphers, not Python's narrower list. `icy` asks for the titles
    interleaved with the audio."""
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
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if icy:
        headers["Icy-MetaData"] = "1"
    request = urllib.request.Request(url, headers=headers)
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
    def __init__(self, url: str, audio, monitor: MonitorChannel = None):
        self.url = url
        self.audio = audio
        self.trimmer = ReplayTrimmer()
        self.forwarded = 0
        # When ffmpeg got its last bytes: a reconnect whose burst was all
        # dropped does not end the silence.
        self.audio_at = None
        self._quiet_logged_at = float("-inf")
        # STREAM_SINGLE_INPUT: the titles go to the monitor, while ICY
        # metadata works on this upstream.
        self.monitor = monitor
        self.icy = monitor is not None and not os.path.exists(NO_TITLES_FLAG)
        # Titles read in bytes the trimmer has not placed yet (a reconnect's
        # burst): they go out once those bytes are forwarded or dropped, so
        # a title is never dated before its audio reaches ffmpeg.
        self.pending_titles = []

    def run(self) -> int:
        """Relays until ffmpeg is gone (BrokenPipeError) or the upstream is
        one only ffmpeg reads; never gives up on an unreachable one."""
        failures = 0  # failed attempts in a row
        unsupported = 0  # of them, the latest in a row only ffmpeg may read
        while True:
            reason = None
            try:
                response = _open(self.url, icy=self.icy)
            except (OSError, http.client.HTTPException, ValueError,
                    Unsupported) as e:
                if not self.forwarded:
                    reason = _unsupported_reason(e)
                if reason and self.icy:
                    # Maybe the answer to Icy-MetaData only: without it.
                    self._titles_unavailable(
                        f"asking for ICY metadata failed ({reason})")
                    continue
                unsupported = unsupported + 1 if reason else 0
                self._attempt_failed(failures, f"connect failed ({_describe(e)})")
            except Exception as e:  # noqa: BLE001 - a bug must not end the stream
                unsupported = 0
                self._unexpected(e)
            else:
                unsupported = 0
                try:
                    healthy = self._pump(response)
                except BrokenPipeError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self._unexpected(e)
                    healthy = False
                finally:
                    response.close()
                if healthy:
                    failures = 0
                    continue
            # Every attempt so far, so not a passing glitch.
            if unsupported >= UNSUPPORTED_ATTEMPTS and unsupported > failures:
                return self._unsupported(reason)
            time.sleep(RETRY_DELAYS[min(failures, len(RETRY_DELAYS) - 1)])
            failures += 1

    def _attempt_failed(self, failures: int, message: str):
        """Logs a failed attempt: each of the first ones, then one a minute
        while the upstream stays down."""
        now = time.monotonic()
        if failures < LOGGED_FAILURES:
            _log(message)
        elif now - self._quiet_logged_at >= QUIET_LOG_SECONDS:
            _log(f"{message}; still retrying ({failures + 1} attempts)")
        else:
            return
        self._quiet_logged_at = now

    def _unexpected(self, e: Exception):
        """An error the relay does not expect: logged and reported, then
        handled as a failed attempt, so ffmpeg keeps its input."""
        _log(f"unexpected {_describe(e)}, reconnecting")
        if posthog_reporter is not None:
            posthog_reporter.capture_exception(e, {"component": "input_relay"})
        if self.icy:
            # Maybe the new metadata path: titles must never cost audio.
            self._titles_unavailable(f"unexpected {_describe(e)}")

    def _pump(self, response) -> bool:
        """Forwards one connection until it ends. Whether it did not fail:
        it gave audio, then went silent or lasted STABLE_SECONDS."""
        reconnect = self.audio_at is not None
        if reconnect:
            self.trimmer.reconnected()
        else:
            _log(f"connected ({response.headers.get('Content-Type')})")
        connected_at = time.monotonic()
        demuxer = self._demuxer(response)
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
                if demuxer:
                    data = self._take_titles(demuxer, data)
                self._write(self.trimmer.feed(data))
                self._send_titles_once_placed()
                if demuxer and demuxer.out_of_step:
                    self._titles_unavailable(demuxer.out_of_step)
                    break  # the next connection comes without metadata
                if self.trimmer.holding and (
                        now - connected_at >= PLACE_SECONDS):
                    self._write(self.trimmer.give_up())
                    self._send_titles_once_placed()
                if not reported and not self.trimmer.placing:
                    reported = True
                    self._report_reconnect(silent_s, response)
        except BrokenPipeError:
            raise
        except (OSError, http.client.HTTPException) as e:
            timed_out = isinstance(e, (socket.timeout, TimeoutError))
            _log(f"{_describe(e)}, reconnecting")
        self._write(self.trimmer.connection_ended())
        self._send_titles_once_placed()
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
            if self.monitor:
                self.monitor.audio_sent(time.time())

    def _demuxer(self, response):
        """The ICY demuxer for this connection, or None without metadata."""
        if not self.icy:
            return None
        try:
            metaint = int(response.headers.get("icy-metaint") or 0)
        except ValueError:
            metaint = 0
        if metaint <= 0:
            self._titles_unavailable("no icy-metaint header")
            return None
        return IcyDemuxer(metaint)

    def _take_titles(self, demuxer: IcyDemuxer, data: bytes) -> bytes:
        """The audio in `data`; its titles wait in pending_titles."""
        audio, blocks = demuxer.feed(data)
        for fields in blocks:
            title = fields.get(b"StreamTitle")
            if title is not None:
                self.pending_titles.append(decode_title(title))
        return audio

    def _send_titles_once_placed(self):
        if self.pending_titles and not self.trimmer.placing:
            now = time.time()
            for title in self.pending_titles:
                self.monitor.title_read(title, now)
            self.pending_titles.clear()

    def _titles_unavailable(self, reason: str):
        """The monitor reads the titles over its own connection from now
        on (for the container's life), and the relay asks for none."""
        self.icy = False
        _log(f"no titles from this upstream ({reason}); metadata_monitor "
             "reads them itself")
        try:
            with open(NO_TITLES_FLAG, "w") as f:
                f.write(reason + "\n")
        except OSError as e:
            _log(f"could not write {NO_TITLES_FLAG} ({e})")
        if posthog_reporter is not None:
            posthog_reporter.capture_event("relay_titles_unavailable",
                                           {"reason": reason})

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
    monitor = MonitorChannel() if SINGLE_INPUT else None
    try:
        return Relay(argv[1], audio, monitor).run()
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    code = main(sys.argv)
    sys.stderr.flush()
    # Skips exit hooks: posthog's final flush could hold up the restart.
    os._exit(code)
