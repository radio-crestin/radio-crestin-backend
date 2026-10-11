"""
Wall-clock EXT-X-PROGRAM-DATE-TIME for ffmpeg's HLS segments.

ffmpeg's `program_date_time` is time() at muxer init plus the cumulative
media duration, and it is never re-anchored. A connect burst (the source
sends the last N seconds at once) pushes it ahead of the wall clock; an
upstream stall followed by an in-process reconnect drags it behind. Measured
in production: -4519 s to +111 s. Every other timestamp of the pipeline (song
start, EXT-X-DATERANGE, EXT-X-RC-METADATA-CHANGED, the API history) is wall
clock, so playlist_rewriter stamps every segment itself:

* A segment is *paced* when it finished at least PACED_MIN_GAP after its
  predecessor. Burst segments finish milliseconds apart; a paced segment's
  last sample arrived in real time, so `mtime - EXTINF` is the wall-clock
  time its first sample aired (its *anchor*).
* A new ffmpeg boot is held back until a paced segment exists. The boot's
  earlier segments are back-chained from the newest paced segment, which
  dates the burst audio when it actually aired.
* Inside a boot each stamp follows the media chain (previous stamp plus
  previous EXTINF). It moves forward to the anchor only when two consecutive
  paced segments agree the chain is more than REANCHOR_THRESHOLD behind (an
  upstream stall), by the smaller of the two residuals. A burst inside a
  boot (in-process reconnect) is held and dated from the first paced
  segment after it, like a boot.
* RFC 8216 6.2.1 forbids a PDT that makes the date-to-segment mapping
  ambiguous, so stamps never overlap: they only move forward, also across
  a discontinuity. Replayed audio that stays published therefore leaves the
  stamps ahead of the wall clock by the replayed length; `Stamp.ahead`
  tracks such an episode so it is reported once (kind `replay`).
* That drift is bounded by MAX_DRIFT. Segments that would put the stamps
  further ahead are withheld (stamped, marked unpublished) instead, and the
  rewriter puts EXT-X-DISCONTINUITY before the next published one: a burst
  replaying published audio (inside a boot or at a new boot, kind
  `duplicate`) and, once the chain is confirmed more than MAX_DRIFT ahead,
  new audio until the stamps are back within MAX_DRIFT (kind `resync`).
* Leading segments of a new boot whose audio aired before the previous
  boot's last published sample (a reconnect burst replaying audio already
  published) are withheld. When the previous boot ran ahead, its stamps end
  later than its audio (BootEnd): the new boot's audio in between is new
  and is published, starting where the previous stamps end, so at most
  MAX_DRIFT carries over.
* A stamp is computed once and never changes (RFC 8216 6.2.1): callers
  persist it with the segment.

Consequence for clients: PDT advances by at least the previous EXTINF and
jumps forward wherever audio was lost, also between two segments of one
window. A playhead must be mapped to the segment that contains it and that
segment's PDT; extrapolating `first PDT + position` across segments is wrong.

Pure functions only: playlist_rewriter supplies the file mtimes and stores
the results, which keeps this module unit-testable without a filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

# A segment finishing at least this long after its predecessor received its
# last sample in real time. Burst segments finish within a few hundred ms of
# each other even on a throttled CPU; steady segments ~EXTINF apart.
PACED_MIN_GAP = 1.0
# Chain error tolerated before re-anchoring. Smaller than the app's 10 s
# lookup windows, larger than mtime jitter (measured < 0.1 s).
REANCHOR_THRESHOLD = 2.0
# The two residuals that confirm a re-anchor (or a drift ahead) must agree
# this closely.
CONFIRM_TOLERANCE = 1.0
# How far the stamps may stay ahead of the wall clock: one segment, about
# the app's 10 s song lookup windows. A replay that would exceed it is
# withheld (one EXT-X-DISCONTINUITY) instead of shifting every later PDT; a
# short replay pushing past it is withheld once the next segment confirms
# it, so a single published segment can briefly be up to two segments ahead.
MAX_DRIFT = 6.0
# A boot whose segments never arrive paced is stamped from its newest
# segment after this long, so a misbehaving source cannot hide the stream.
BOOT_ANCHOR_TIMEOUT = 20.0
# Slack when comparing a new boot's first stamps with the previous boot.
OVERLAP_TOLERANCE = 0.05

KIND_BOOT = "boot"
KIND_BOOT_FALLBACK = "boot-fallback"
KIND_CHAIN = "chain"
KIND_REANCHOR = "reanchor"
KIND_DUPLICATE = "duplicate"
# The segment that confirms a drift-ahead episode: audio already published
# was replayed, so the stamps stay ahead of the wall clock by the replayed
# length (at most MAX_DRIFT). Its residual is minus the drift.
KIND_REPLAY = "replay"
# New audio withheld because the stamps ran more than MAX_DRIFT ahead.
KIND_RESYNC = "resync"
WITHHELD_KINDS = (KIND_DUPLICATE, KIND_RESYNC)


@dataclass(frozen=True)
class Observation:
    """A segment from ffmpeg's playlist plus its file mtime."""

    name: str
    duration: float
    mtime: float | None


@dataclass(frozen=True)
class Stamp:
    """The wall-clock date assigned once to a segment.

    `residual` is anchor minus stamp (None without an mtime): positive when
    the stamp is behind the wall clock, negative when ahead. `ahead` is True
    for every stamp of a confirmed drift-ahead episode (replayed audio).
    """

    name: str
    duration: float
    mtime: float | None
    wall: float
    paced: bool
    residual: float | None
    kind: str
    ahead: bool = False

    @property
    def end(self) -> float:
        return self.wall + self.duration

    @property
    def published(self) -> bool:
        return self.kind not in WITHHELD_KINDS


@dataclass(frozen=True)
class BootEnd:
    """Where the published segments end, in two clocks.

    `pdt` is the end of the last published stamp: no later stamp may start
    before it (RFC 8216 6.2.1). `audio` is when that segment's last sample
    arrived. It is earlier than `pdt` when the stamps ran ahead of the wall
    clock (audio replayed in-process), and never earlier than the sample
    aired. A later segment that aired before `audio` replays published
    audio; one that aired after it is new audio, published from `pdt` on
    unless that is more than MAX_DRIFT after it aired.
    """

    pdt: float
    audio: float


def boot_end(last: Stamp) -> BootEnd:
    """The BootEnd of a boot whose newest published stamp is `last`.

    A stamp ahead of its audio ends after its file was written (negative
    residual); its mtime is then where the audio ends. Otherwise the stamp
    end is kept, as without drift.
    """
    if last.mtime is None:
        return BootEnd(pdt=last.end, audio=last.end)
    return BootEnd(pdt=last.end, audio=min(last.end, last.mtime))


def _placed_after(wall: float, floor: BootEnd | None) -> float | None:
    """Where a segment that aired at `wall` is published when it is the
    first of a new boot or follows withheld segments.

    None when it replays published audio, or when following the published
    stamps would put it more than MAX_DRIFT ahead. Other new audio that
    aired before those stamps ended (they ran ahead) starts at their end,
    so PDT never goes back.
    """
    if floor is None:
        return wall
    if wall < floor.audio - OVERLAP_TOLERANCE:
        return None
    if wall < floor.pdt - MAX_DRIFT - OVERLAP_TOLERANCE:
        return None
    return floor.pdt if wall < floor.pdt - OVERLAP_TOLERANCE else wall


def _withheld_kind(wall: float, floor: BootEnd) -> str:
    """Why a segment that aired at `wall` is not published."""
    if wall < floor.audio - OVERLAP_TOLERANCE:
        return KIND_DUPLICATE
    return KIND_RESYNC


def _first_new_audio(walls: list[float],
                     floor: BootEnd | None) -> tuple[int, float]:
    """Index of a new boot's first segment that is not a replay, and how
    far it and every later segment move forward to follow the previous
    boot's stamps (0 when they already do). len(walls) when all replay."""
    for i, wall in enumerate(walls):
        placed = _placed_after(wall, floor)
        if placed is not None:
            return i, placed - wall
    return len(walls), 0.0


def boot_of(name: str) -> str:
    """`<slug>-<boot>` prefix of a `<slug>-<boot>-<n>.ts` segment name."""
    return name.rsplit("-", 1)[0]


def _paced(obs: Observation, prev_mtime: float | None) -> bool:
    if obs.mtime is None or prev_mtime is None:
        return False
    return obs.mtime - prev_mtime >= PACED_MIN_GAP


def _anchor(obs: Observation) -> float | None:
    return None if obs.mtime is None else obs.mtime - obs.duration


def _residual(obs: Observation, wall: float) -> float | None:
    anchor = _anchor(obs)
    return None if anchor is None else anchor - wall


def _agree(a: float | None, b: float | None) -> bool:
    return (a is not None and b is not None
            and abs(a - b) <= CONFIRM_TOLERANCE)


def anchor_new_boot(pending: list[Observation], now: float,
                    floor: BootEnd | None) -> list[Stamp]:
    """Stamp the held-back first segments of a boot, or return [] to wait.

    `pending` holds every not-yet-stamped segment of the boot in playlist
    order; `floor` is where the last published segment of an earlier boot
    ends (None when there is none).
    """
    if not pending:
        return []
    # The newest paced segment: right after a connect burst it is the first
    # one; when a restarted rewriter finds a long-running boot it is the
    # live edge, which is what listeners hear first.
    anchor_idx = max((i for i in range(1, len(pending))
                      if _paced(pending[i], pending[i - 1].mtime)),
                     default=None)
    kind = KIND_BOOT
    if anchor_idx is None:
        first = pending[0].mtime if pending[0].mtime is not None else now
        if now - first < BOOT_ANCHOR_TIMEOUT or pending[-1].mtime is None:
            return []
        anchor_idx, kind = len(pending) - 1, KIND_BOOT_FALLBACK
    walls = [0.0] * len(pending)
    walls[anchor_idx] = _anchor(pending[anchor_idx])
    for i in range(anchor_idx - 1, -1, -1):
        walls[i] = walls[i + 1] - pending[i].duration
    for i in range(anchor_idx + 1, len(pending)):
        walls[i] = walls[i - 1] + pending[i - 1].duration
    return _follow(pending, walls, floor, kind, anchor_idx)


def _follow(pending: list[Observation], walls: list[float],
            floor: BootEnd | None, kind: str,
            anchor_idx: int) -> list[Stamp]:
    """Stamps for `pending`, whose audio aired at `walls`, following the
    published stamps that end at `floor`: the leading segments
    _placed_after places nowhere are withheld, the rest published as
    `kind`."""
    first, shift = _first_new_audio(walls, floor)
    ahead = shift > REANCHOR_THRESHOLD
    # A carried drift is reported where it is measured: on the anchor
    # (residual = -drift), or on the first published segment when the
    # anchor itself replays published audio.
    replay_at = max(first, anchor_idx) if ahead else None
    stamps = []
    for i, obs in enumerate(pending):
        published = i >= first
        wall = walls[i] + shift if published else walls[i]
        if not published:
            stamp_kind = _withheld_kind(walls[i], floor)
        elif i == replay_at:
            stamp_kind = KIND_REPLAY
        else:
            stamp_kind = kind
        stamps.append(Stamp(
            name=obs.name, duration=obs.duration, mtime=obs.mtime,
            wall=wall,
            paced=i > 0 and _paced(obs, pending[i - 1].mtime),
            residual=_residual(obs, wall),
            kind=stamp_kind, ahead=published and ahead,
        ))
    return stamps


def stamp_next(prev: Stamp, obs: Observation,
               floor: BootEnd | None = None) -> Stamp:
    """Stamp the segment that follows `prev` in the same boot.

    `floor` is where the newest published stamp ends. It is only consulted
    after withheld segments (`prev` unpublished): they stay withheld until
    one can follow the published stamps (see _placed_after).
    """
    chain = prev.end
    paced = _paced(obs, prev.mtime)
    residual = _residual(obs, chain)
    if prev.published and _too_far_ahead(prev, residual):
        # Withheld and dated when it aired; the next segment follows the
        # published stamps from `floor` again, one segment less ahead.
        return Stamp(obs.name, obs.duration, obs.mtime, _anchor(obs), paced,
                     0.0, KIND_RESYNC)
    confirmed = (
        paced and residual is not None and residual > REANCHOR_THRESHOLD
        and prev.paced and prev.residual is not None
        and prev.residual > REANCHOR_THRESHOLD
        and _agree(residual, prev.residual)
    )
    if confirmed:
        step = min(residual, prev.residual)
        stamp = Stamp(obs.name, obs.duration, obs.mtime, chain + step,
                      paced, residual - step, KIND_REANCHOR)
    else:
        ahead = _drifts_ahead(prev, residual)
        kind = KIND_REPLAY if ahead and not prev.ahead else KIND_CHAIN
        stamp = Stamp(obs.name, obs.duration, obs.mtime, chain, paced,
                      residual, kind, ahead)
    if prev.published or floor is None:
        return stamp
    return _after_replayed_audio(stamp, obs, floor)


def _after_replayed_audio(stamp: Stamp, obs: Observation,
                          floor: BootEnd) -> Stamp:
    """`stamp` (of `obs`, dated when its audio aired) right after withheld
    segments: still withheld, or the first published segment after them,
    moved forward to follow the published stamps when those ran ahead."""
    placed = _placed_after(stamp.wall, floor)
    if placed is None:
        return replace(stamp, kind=_withheld_kind(stamp.wall, floor),
                       ahead=False)
    if placed == stamp.wall:
        return stamp
    ahead = placed - stamp.wall > REANCHOR_THRESHOLD
    return replace(stamp, wall=placed, residual=_residual(obs, placed),
                   ahead=ahead, kind=KIND_REPLAY if ahead else stamp.kind)


def _too_far_ahead(prev: Stamp, residual: float | None) -> bool:
    """True when two consecutive residuals agree that the chain runs more
    than MAX_DRIFT ahead of the wall clock (short replays add up)."""
    return (residual is not None and residual < -MAX_DRIFT
            and prev.residual is not None and prev.residual < -MAX_DRIFT
            and _agree(residual, prev.residual))


def _drifts_ahead(prev: Stamp, residual: float | None) -> bool:
    """True while the chain is confirmed ahead of the wall clock.

    A replay shorter than one segment never forms a burst, yet it leaves the
    chain ahead by the replayed length. The clock cannot move back (RFC 8216
    6.2.1); up to MAX_DRIFT this only reports: two consecutive residuals below
    -REANCHOR_THRESHOLD that agree start an episode, which lasts until the
    residual comes back above the threshold.
    """
    if residual is None or residual >= -REANCHOR_THRESHOLD:
        return False
    if prev.ahead:
        return True
    return (prev.residual is not None
            and prev.residual < -REANCHOR_THRESHOLD
            and _agree(residual, prev.residual))


def is_burst(obs: Observation, prev_mtime: float | None) -> bool:
    """True when `obs` completed right after its predecessor: its audio
    arrived faster than real time (a reconnect burst or a write backlog)."""
    return (obs.mtime is not None and prev_mtime is not None
            and obs.mtime - prev_mtime < PACED_MIN_GAP)


def stamp_burst(prev: Stamp, held: list[Observation],
                now: float) -> list[Stamp]:
    """Stamp a burst inside a boot, or return [] to keep holding it.

    `held` starts with the segment that completed right after `prev` and
    holds the following segments of the same boot in order. The burst is
    dated from the first paced segment after it, exactly like a boot: when
    the chain is more than REANCHOR_THRESHOLD behind that anchor (audio was
    lost in a stall), the burst moves forward to it at once; when chaining
    would leave the stamps more than MAX_DRIFT ahead (replayed audio), the
    segments replaying published audio are withheld, as at a new boot;
    otherwise (jitter, a short replay) it chains. Returns stamps for the
    burst and its anchor only. A replay is marked on the anchor, the
    segment whose timing measured it (residual = -drift).
    """
    anchor_idx = next((i for i in range(1, len(held))
                       if _paced(held[i], held[i - 1].mtime)), None)
    if anchor_idx is None:
        first = held[0].mtime if held[0].mtime is not None else now
        if now - first < BOOT_ANCHOR_TIMEOUT:
            return []
        anchor_idx = len(held) - 1
        back = None
    else:
        back = [0.0] * (anchor_idx + 1)
        back[anchor_idx] = _anchor(held[anchor_idx])
        for i in range(anchor_idx - 1, -1, -1):
            back[i] = back[i + 1] - held[i].duration
    shift = None if back is None else back[0] - prev.end
    if shift is not None and shift < -MAX_DRIFT:
        return _follow(held[:anchor_idx + 1], back, boot_end(prev),
                       KIND_REANCHOR, anchor_idx)
    jump =shift is not None and shift > REANCHOR_THRESHOLD
    replay = shift is not None and shift < -REANCHOR_THRESHOLD
    # Without an anchor (timeout) nothing new is known about the drift.
    ahead = prev.ahead if shift is None else replay
    stamps: list[Stamp] = []
    wall = back[0] if jump else prev.end
    for i, o in enumerate(held[:anchor_idx + 1]):
        if jump and i == 0:
            kind = KIND_REANCHOR
        elif replay and i == anchor_idx:
            kind = KIND_REPLAY  # replayed audio: the chain is ahead by -shift
        else:
            kind = KIND_CHAIN
        stamps.append(Stamp(
            name=o.name, duration=o.duration, mtime=o.mtime, wall=wall,
            paced=i == anchor_idx and back is not None,
            residual=_residual(o, wall), kind=kind, ahead=ahead,
        ))
        wall += o.duration
    return stamps
