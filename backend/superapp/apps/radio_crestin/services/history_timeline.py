"""Where a new now-playing history row goes on its station's timeline.

The API answers "what was playing at T" from these rows (/stations-metadata
and /stations-metadata-history), so every writer places its rows through
`stamp_history_row`. A row carries two instants:

* `timestamp` orders the station's rows and says when a row can still
  appear. It is never more than METADATA_BACKDATE_LIMIT before the row is
  written, which the REST layer's settle window and diff lookback rely on,
  and it is strictly after the station's newest row (rows dated in the far
  future aside, see _UNREACHABLE_FUTURE), so a `timestamp <= T` lookup has
  exactly one newest row.
* `song_started_at` is the song start the API shows. A listener-count row
  repeats the start of the song it belongs to, so a changing audience never
  makes a song look as if it started again.

Report writers (pods and Celery scrapes) go through `place_report`, which
also keeps now_playing.timestamp the start of the current song.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Optional, Tuple

from superapp.apps.radio_crestin.models import StationsNowPlayingHistory

# How far before its insertion a history row may be dated. Pods date a song
# change by when it started in the stream and report it seconds later. The
# REST layer relies on this bound (plus margin) to know when an answer for a
# timestamp can no longer change (METADATA_SETTLE_SECONDS) and how far a
# changes_from_timestamp diff must look back (CHANGES_LOOKBACK_SECONDS).
METADATA_BACKDATE_LIMIT = timedelta(seconds=45)
# A pod may date a song slightly in the future (a negative ID3 delay offset
# means the title is announced before the audio); more than this is a bad
# clock, not an offset.
METADATA_FUTURE_LIMIT = timedelta(seconds=60)
# Rows dated further ahead than this were never placed by these rules (a bad
# clock before METADATA_FUTURE_LIMIT existed); the limit plus as much again
# for clock skew between web pods. New rows are not ordered after them:
# that would date them in the far future, where no lookup sees them.
_UNREACHABLE_FUTURE = 2 * METADATA_FUTURE_LIMIT
# Gap that keeps a station's timestamps and song starts strictly increasing.
HISTORY_TIMESTAMP_STEP = timedelta(milliseconds=1)


@dataclass(frozen=True)
class HistoryStamp:
    """The two instants of a new history row (see the module docstring)."""

    timestamp: datetime
    # None only for a listener-count row of a station without an earlier
    # row to take its song start from.
    song_started_at: Optional[datetime]


def stamp_history_row(station_id: int, event_ts: datetime, now: datetime,
                      song_changed: bool) -> HistoryStamp:
    """Place a new history row of `station_id` describing `event_ts`.

    `event_ts` is when a song change began in the stream, or `now` for a
    listener-count change. The caller must hold the station's row lock
    (`select_for_update(no_key=True)`), so concurrent writers never pick
    the same timestamp.

    A song change normally gets `timestamp == song_started_at ==` the
    clamped `event_ts`. When a row of the previous song was written after
    this song began, the new row is ordered after that row but keeps its
    real start, so `song_started_at <= timestamp` always holds.
    """
    clamped = min(max(event_ts, now - METADATA_BACKDATE_LIMIT),
                  now + METADATA_FUTURE_LIMIT)
    newest = _newest_row(station_id, now)
    if newest is None:
        return HistoryStamp(clamped, clamped if song_changed else None)

    newest_timestamp, newest_song_start = newest
    timestamp = max(clamped, newest_timestamp + HISTORY_TIMESTAMP_STEP)
    if not song_changed:
        return HistoryStamp(timestamp, newest_song_start)
    # A song never starts before the one it replaces: equal starts would
    # make the API list two songs at one instant.
    song_started_at = max(clamped, newest_song_start + HISTORY_TIMESTAMP_STEP)
    return HistoryStamp(timestamp, song_started_at)


@dataclass(frozen=True)
class PlacedReport:
    """A now-playing report placed on its station's timeline."""

    # now_playing.timestamp: when the current song started. It moves only
    # when the song changes and never shows a start after the report.
    song_started_at: datetime
    # The history row to write, or None when neither the song nor the
    # listener count changed.
    history: Optional[HistoryStamp]


def place_report(station_id: int, previous: Optional[dict],
                 song_id: Optional[int], listeners: Optional[int],
                 song_start: datetime, now: datetime) -> PlacedReport:
    """Place a report that `song_id` is playing to `listeners`.

    `previous` is the station's StationsNowPlaying as
    `values('song_id', 'listeners', 'timestamp')`, or None. `song_start`
    dates the song if it changed. The caller must hold the station's row
    lock, as for `stamp_history_row`.
    """
    song_changed = previous is None or previous['song_id'] != song_id
    listeners_changed = previous is None or previous['listeners'] != listeners
    history = None
    if song_changed or listeners_changed:
        # A listener-count change is a measurement taken now; dating it by
        # the song start would back-date it by minutes.
        event_ts = song_start if song_changed else now
        history = stamp_history_row(station_id, event_ts, now, song_changed)

    if song_changed:
        # A start announced ahead of the audio shows as now until then.
        started = min(history.song_started_at, now)
    else:
        started = previous['timestamp']
    if history is not None and history.song_started_at is None:
        # Without an earlier history row, now_playing still knows when the
        # continuing song started.
        history = replace(history, song_started_at=started)
    return PlacedReport(started, history)


def _newest_row(station_id: int,
                now: datetime) -> Optional[Tuple[datetime, datetime]]:
    """`(timestamp, song start)` of the station's newest reachable row."""
    row = (
        StationsNowPlayingHistory.objects
        .filter(station_id=station_id,
                timestamp__lte=now + _UNREACHABLE_FUTURE)
        .order_by('-timestamp', '-id')
        .values_list('timestamp', 'song_started_at')
        .first()
    )
    if row is None:
        return None
    timestamp, song_started_at = row
    return timestamp, song_started_at or timestamp
