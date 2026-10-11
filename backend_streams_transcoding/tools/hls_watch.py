"""Watch served HLS playlists and check the streamer's playlist contract.

For the canary of a streamer image (and any later spot check): polls each
playlist URL (a station's index.m3u8 and/or dvr.m3u8), feeds every new
version to PlaylistChecker, and prints each violation at once plus a summary
every --report minutes and at the end.

  python3 tools/hls_watch.py https://live.radiocrestin.ro/hls/<slug>/index.m3u8 \\
      https://live.radiocrestin.ro/hls/<slug>/dvr.m3u8 --hours 24

Checked, per playlist URL, across all versions seen (RFC 8216 6.2.1/6.2.2
and the contract in live_streaming/scripts/playlist_rewriter.py):
  * a segment URI keeps its media sequence number, discontinuity number and
    PDT in every version;
  * EXT-X-MEDIA-SEQUENCE and EXT-X-DISCONTINUITY-SEQUENCE never go back;
  * PDT never overlaps the previous segment (it may jump forward);
  * a DATERANGE never changes its attributes and is not removed while its
    range still overlaps the playlist;
  * the EXT-X-RC-METADATA-CHANGED of one EPOCH keeps its STARTED-AT, and an
    X-* hint never changes value (hints may appear seconds after the EPOCH,
    and are withdrawn when a later song is dated by the scrape);
  * the oldest listed segment still answers (HEAD) one poll later.

Also noted, but not a violation: Last-Modified minus the live edge (last PDT
+ EXTINF) outside [EDGE_LAG_MIN, EDGE_LAG_MAX] seconds. Above the range the
edge is stale (a source stall, a held-back run, a stuck rewriter); below it
the PDT runs ahead (replayed audio after an in-process reconnect, until the
next ffmpeg run). Short episodes are expected; one that lasts is not.

Standard library only; no repository imports, so it runs anywhere.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

# Last-Modified minus live edge, seconds. The rewriter publishes a segment
# within ~1 s of its completion, a burst hold-back adds up to one segment.
EDGE_LAG_MIN = -1.0
EDGE_LAG_MAX = 7.0
OVERLAP_TOLERANCE = 0.05
DATERANGE_GRACE = 2.0

_ATTR = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)')


def _epoch(iso: str) -> float:
    iso = iso.strip().strip('"').replace("Z", "+00:00")
    iso = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", iso)
    return datetime.fromisoformat(iso).timestamp()


def attributes(line: str) -> dict[str, str]:
    """RFC 8216 attribute list of a tag line; quoted values keep quotes."""
    return dict(_ATTR.findall(line.split(":", 1)[1]))


@dataclass
class Segment:
    uri: str
    seq: int
    disc: int
    pdt: float | None
    duration: float


@dataclass
class Playlist:
    segments: list[Segment]
    dateranges: dict[str, str]
    metadata_changed: dict[str, str] | None
    start: str | None


def parse(text: str) -> Playlist:
    seq = disc = 0
    segments, dateranges = [], {}
    metadata_changed = start = None
    pdt, duration = None, 0.0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            seq = int(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-DISCONTINUITY-SEQUENCE:"):
            disc = int(line.split(":", 1)[1])
        elif line == "#EXT-X-DISCONTINUITY":
            disc += 1
        elif line.startswith("#EXTINF:"):
            duration = float(line[8:].split(",", 1)[0])
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            pdt = _epoch(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-DATERANGE:"):
            dateranges[attributes(line).get("ID", "").strip('"')] = line
        elif line.startswith("#EXT-X-RC-METADATA-CHANGED:"):
            metadata_changed = attributes(line)
        elif line.startswith("#EXT-X-START:"):
            start = line
        elif line and not line.startswith("#"):
            segments.append(Segment(line, seq, disc, pdt, duration))
            seq += 1
            pdt, duration = None, 0.0
    return Playlist(segments, dateranges, metadata_changed, start)


@dataclass
class PlaylistChecker:
    """Contract checks across successive versions of one playlist URL."""

    seen: dict[str, tuple[int, int, float | None]] = field(
        default_factory=dict)
    last: Playlist | None = None
    epochs: dict[str, dict[str, str]] = field(default_factory=dict)
    edge_lags: list[float] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    versions: int = 0

    def feed(self, text: str, last_modified: float | None) -> list[str]:
        """Contract violations of this version (edge notes go to .notes)."""
        playlist = parse(text)
        problems: list[str] = []
        if playlist.segments:
            problems += self._segments(playlist)
            problems += self._dateranges(playlist)
            self._edge(playlist, last_modified)
        problems += self._metadata_changed(playlist)
        if playlist.start is None:
            problems.append("no EXT-X-START")
        self.last = playlist
        self.versions += 1
        return problems

    def _segments(self, playlist: Playlist) -> list[str]:
        problems = []
        first = playlist.segments[0]
        if self.last and self.last.segments:
            prev = self.last.segments[0]
            if first.seq < prev.seq:
                problems.append(f"MEDIA-SEQUENCE went back {prev.seq} -> "
                                f"{first.seq}")
            if first.disc < prev.disc:
                problems.append(f"DISCONTINUITY-SEQUENCE went back "
                                f"{prev.disc} -> {first.disc}")
        for a, b in zip(playlist.segments, playlist.segments[1:]):
            if (a.pdt is not None and b.pdt is not None
                    and b.pdt < a.pdt + a.duration - OVERLAP_TOLERANCE):
                problems.append(f"PDT overlap {a.uri} -> {b.uri}")
        for s in playlist.segments:
            key = (s.seq, s.disc, s.pdt)
            old = self.seen.setdefault(s.uri, key)
            if old != key:
                problems.append(f"{s.uri} changed (seq, disc, pdt) "
                                f"{old} -> {key}")
                self.seen[s.uri] = key
        return problems

    def _dateranges(self, playlist: Playlist) -> list[str]:
        if not self.last:
            return []
        problems = []
        first_pdt = playlist.segments[0].pdt
        for rid, line in self.last.dateranges.items():
            now = playlist.dateranges.get(rid)
            if now is not None and now != line:
                problems.append(f"DATERANGE {rid} attributes changed")
            end = attributes(line).get("END-DATE")
            if (now is None and end and first_pdt is not None
                    and _epoch(end) > first_pdt - DATERANGE_GRACE):
                problems.append(f"DATERANGE {rid} removed while mapped")
        return problems

    def _metadata_changed(self, playlist: Playlist) -> list[str]:
        """Compare with the first value each attribute had for this EPOCH
        (a withdrawn hint must not come back different)."""
        attrs = playlist.metadata_changed
        if not attrs or "EPOCH" not in attrs:
            return []
        known = self.epochs.setdefault(attrs["EPOCH"], {})
        problems = []
        for name, value in attrs.items():
            if name == "EPOCH":
                continue
            first = known.setdefault(name, value)
            if first != value:
                problems.append(f"EPOCH {attrs['EPOCH']} changed {name}")
        return problems

    def _edge(self, playlist: Playlist, last_modified: float | None) -> None:
        last = playlist.segments[-1]
        if last_modified is None or last.pdt is None:
            return
        lag = last_modified - (last.pdt + last.duration)
        self.edge_lags.append(lag)
        if lag > EDGE_LAG_MAX:
            self.notes.append(f"live edge stale: Last-Modified - edge = "
                              f"{lag:.1f}s")
        elif lag < EDGE_LAG_MIN:
            self.notes.append(f"PDT ahead of Last-Modified by {-lag:.1f}s")


def _fetch(url: str, method: str = "GET", timeout: float = 10.0):
    request = urllib.request.Request(url, method=method, headers={
        "User-Agent": "radio-crestin-hls-watch", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", "replace") \
            if method == "GET" else ""
        modified = response.headers.get("Last-Modified")
        return body, (parsedate_to_datetime(modified).timestamp()
                      if modified else None)


def _head_ok(url: str) -> bool:
    try:
        _fetch(url, "HEAD")
        return True
    except (urllib.error.URLError, OSError):
        return False


def _summary(url: str, checker: PlaylistChecker, problems: int,
             head_checks: int, head_failures: int) -> str:
    lags = sorted(checker.edge_lags)
    lag = (f"edge lag min/median/max {lags[0]:.1f}/"
           f"{lags[len(lags) // 2]:.1f}/{lags[-1]:.1f}s" if lags
           else "edge lag n/a")
    return (f"{url}: {checker.versions} versions, {problems} problems, "
            f"{len(checker.notes)} edge notes, {lag}, "
            f"oldest segment gone {head_failures}/{head_checks}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--interval", type=float, default=6.0)
    parser.add_argument("--hours", type=float, default=24.0)
    parser.add_argument("--report", type=float, default=30.0,
                        help="minutes between summaries")
    args = parser.parse_args(argv)

    checkers = {url: PlaylistChecker() for url in args.urls}
    bodies = {url: None for url in args.urls}
    problems = {url: 0 for url in args.urls}
    heads = {url: [0, 0] for url in args.urls}
    pending_heads: list[tuple[float, str, str]] = []
    end = time.time() + args.hours * 3600
    next_report = time.time() + args.report * 60
    while time.time() < end:
        now = time.time()
        for due, url, segment in [p for p in pending_heads if p[0] <= now]:
            pending_heads.remove((due, url, segment))
            heads[url][0] += 1
            if not _head_ok(segment):
                heads[url][1] += 1
                print(f"{time.strftime('%H:%M:%S')} {url}: oldest segment "
                      f"{segment} gone one poll later", flush=True)
        for url, checker in checkers.items():
            try:
                body, modified = _fetch(url)
            except (urllib.error.URLError, OSError) as e:
                print(f"{time.strftime('%H:%M:%S')} {url}: fetch failed: {e}",
                      flush=True)
                continue
            if body == bodies[url]:
                continue
            bodies[url] = body
            notes = len(checker.notes)
            for problem in checker.feed(body, modified):
                problems[url] += 1
                print(f"{time.strftime('%H:%M:%S')} {url}: {problem}",
                      flush=True)
            for note in checker.notes[notes:]:
                print(f"{time.strftime('%H:%M:%S')} {url}: note: {note}",
                      flush=True)
            segments = checker.last.segments
            if segments:
                pending_heads.append((now + args.interval, url,
                                      urljoin(url, segments[0].uri)))
        if time.time() >= next_report:
            next_report += args.report * 60
            for url, checker in checkers.items():
                print(_summary(url, checker, problems[url], *heads[url]),
                      flush=True)
        time.sleep(args.interval)
    for url, checker in checkers.items():
        print(_summary(url, checker, problems[url], *heads[url]), flush=True)
    failed = any(problems.values()) or any(h[1] for h in heads.values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
