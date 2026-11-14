"""Records the HLS listening events the streaming pods submit.

Every pod with listeners sends a batch every 10 s (log_monitor.py), one
event per listening session (about 15,000 batches an hour). A batch is
written with a fixed number of queries whatever its size: one per table to
read the stations, users and active sessions, one insert each for the new
users and sessions, and one update for the sessions that continue.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import connection, transaction
from django.utils import timezone

from ..models import AppUsers, ListeningSessions, Stations

logger = logging.getLogger(__name__)

# A session ends after this long without activity (ListeningSessions).
SESSION_TIMEOUT = timedelta(minutes=5)

# The columns an event changes on a session, besides is_active and updated_at.
ACTIVITY_COLUMNS = (
    ('last_activity', 'timestamptz'), ('total_requests', 'integer'),
    ('bytes_transferred', 'bigint'), ('playlist_requests', 'integer'),
    ('segment_requests', 'integer'), ('duration_seconds', 'integer'),
)


@dataclass(frozen=True)
class _Event:
    station: Stations
    session_id: str
    timestamp: datetime
    source: object  # the ListeningEventInput


def record_listening_events(events) -> int:
    """Count each event on its listener's active session on its station,
    opening a session when there is none; the number of events recorded."""
    parsed = _parse(events)
    if not parsed:
        return 0
    now = timezone.now()
    with transaction.atomic():
        users = _users_by_anonymous_id({event.session_id for event in parsed})
        sessions = _active_sessions(parsed, users, now - SESSION_TIMEOUT)
        new_sessions, continued = [], {}
        for event in parsed:
            key = (event.station.id, event.session_id)
            session = sessions.get(key)
            if session is None or not _still_active(session, now):
                session = _new_session(users[event.session_id], event, now)
                sessions[key] = session
                new_sessions.append(session)
            elif session.pk is not None:
                continued[session.pk] = session
            _count_activity(session, event, now)
        ListeningSessions.objects.bulk_create(new_sessions)
        _save_activity(continued.values(), now)
    return len(parsed)


def _parse(events) -> list[_Event]:
    """The events with a readable timestamp and a known station."""
    slugs = {event.station_slug for event in events}
    stations = {station.slug: station for station in Stations.objects.filter(slug__in=slugs)}
    for slug in slugs - stations.keys():
        logger.warning("Station not found: %s", slug)
    parsed = []
    for event in events:
        station = stations.get(event.station_slug)
        if station is None:
            continue
        try:
            timestamp = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        except (AttributeError, ValueError) as error:
            logger.error("Error processing individual event: %s", error)
            continue
        parsed.append(_Event(station, event.anonymous_session_id, timestamp, event))
    return parsed


def _users_by_anonymous_id(anonymous_ids) -> dict:
    """The AppUsers of these anonymous ids, created where missing."""
    users = {user.anonymous_id: user for user in AppUsers.objects.filter(anonymous_id__in=anonymous_ids)}
    missing = anonymous_ids - users.keys()
    if missing:
        # A concurrent batch may create the same user: ignore_conflicts keeps
        # its row, and the second read picks it up.
        AppUsers.objects.bulk_create(
            [AppUsers(anonymous_id=anonymous_id) for anonymous_id in missing],
            ignore_conflicts=True,
        )
        users.update(
            (user.anonymous_id, user)
            for user in AppUsers.objects.filter(anonymous_id__in=missing)
        )
    return users


def _active_sessions(events, users, active_since) -> dict:
    """The latest active session per (station id, anonymous session id)."""
    sessions = ListeningSessions.objects.filter(
        station_id__in={event.station.id for event in events},
        anonymous_session_id__in={event.session_id for event in events},
        user_id__in={user.id for user in users.values()},
        is_active=True,
        last_activity__gte=active_since,
    ).order_by('last_activity', 'id')
    latest = {}
    for session in sessions:
        if session.user_id == users[session.anonymous_session_id].id:
            latest[(session.station_id, session.anonymous_session_id)] = session
    return latest


def _still_active(session, now) -> bool:
    """A session met earlier in this batch can have been dated back past
    the timeout by an old event."""
    return session.is_active and session.last_activity >= now - SESSION_TIMEOUT


def _new_session(user, event, now) -> ListeningSessions:
    source = event.source
    return ListeningSessions(
        user=user,
        station=event.station,
        anonymous_session_id=event.session_id,
        start_time=now,
        last_activity=now,
        ip_address=source.ip_address,
        user_agent=source.user_agent,
        referer=source.referer,
        is_active=True,
    )


def _count_activity(session, event, now) -> None:
    """ListeningSessions.update_activity, without the save."""
    session.last_activity = event.timestamp
    session.total_requests += 1
    session.bytes_transferred += event.source.bytes_transferred
    if event.source.event_type == 'playlist_request':
        session.playlist_requests += 1
    else:
        session.segment_requests += 1
    session.duration_seconds = int((session.last_activity - session.start_time).total_seconds())
    session.is_active = True


def _save_activity(sessions, now) -> None:
    """One UPDATE for all continued sessions. QuerySet.bulk_update builds a
    CASE per column and row: for a batch of 7 it took 60% of the request's
    CPU, this statement a fraction of a millisecond."""
    sessions = list(sessions)
    if not sessions:
        return
    columns = ', '.join(name for name, _ in ACTIVITY_COLUMNS)
    row = '(%s::bigint, ' + ', '.join(f'%s::{kind}' for _, kind in ACTIVITY_COLUMNS) + ')'
    assignments = ', '.join(f'{name} = v.{name}' for name, _ in ACTIVITY_COLUMNS)
    params = [now]
    for session in sessions:
        params += [session.pk, *(getattr(session, name) for name, _ in ACTIVITY_COLUMNS)]
    with connection.cursor() as cursor:
        cursor.execute(
            f'UPDATE {ListeningSessions._meta.db_table} AS s '
            f'SET {assignments}, is_active = true, updated_at = %s '
            f'FROM (VALUES {", ".join([row] * len(sessions))}) AS v(id, {columns}) '
            'WHERE s.id = v.id',
            params,
        )
