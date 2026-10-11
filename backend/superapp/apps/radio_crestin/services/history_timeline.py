"""Where a new now-playing history row goes on its station's timeline.

The API answers "what was playing at T" from these rows (/stations-metadata
and /stations-metadata-history), so every writer places its rows through
`stamp_history_row`. A row carries two instants:

* `timestamp` orders the station's rows and says when a row can still
  appear. It is never more than METADATA_BACKDATE_LIMIT before the row is
  written, which the REST layer's settle window and diff lookback rely on,
  and it is strictly after the station's newest row, so a `timestamp <= T`
  lookup has exactly one newest row.
* `song_started_at` is the song start the API shows. A listener-count row
  repeats the start of the song it belongs to, so a changing audience never
  makes a song look as if it started again.
"""

from dataclasses import dataclass
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
    newest = _newest_row(station_id)
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


def _newest_row(station_id: int) -> Optional[Tuple[datetime, datetime]]:
    """`(timestamp, song start)` of the station's newest row, if any."""
    row = (
        StationsNowPlayingHistory.objects
        .filter(station_id=station_id)
        .order_by('-timestamp', '-id')
        .values_list('timestamp', 'song_started_at')
        .first()
    )
    if row is None:
        return None
    timestamp, song_started_at = row
    return timestamp, song_started_at or timestamp
