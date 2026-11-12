"""Stores the events clients report and bumps the totals on each announcement.

The endpoint is public and device ids are unsigned, so repeats are dropped before
they reach the counters: impressions and taps through short-lived cache keys
(DEDUPE_SECONDS), closes through the database (one per announcement and device).
That bounds what one device id can add; it can't stop someone from inventing
many device ids.
"""
import hashlib
from collections import Counter
from datetime import timedelta, timezone as dt_timezone
from typing import Optional

from django.conf import settings
from django.core.cache import caches
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import Announcement, AnnouncementEvent, AnnouncementEventTarget, AnnouncementEventType
from ..models.announcement_events import COUNTER_FIELD_BY_EVENT_TYPE

MAX_EVENTS_PER_REQUEST = 100
MAX_EVENT_AGE = timedelta(hours=24)
MAX_CLOCK_SKEW = timedelta(minutes=5)

MAX_ANNOUNCEMENTS_PER_REQUEST = 10

# Event type -> seconds during which a repeat from the same device for the same announcement is dropped.
# Closes aren't here: they are kept once per device in the database (see _save_new_dismissals).
DEDUPE_SECONDS = {
    AnnouncementEventType.IMPRESSION: 30 * 60,
    AnnouncementEventType.CLICKED: 60,
    AnnouncementEventType.SECONDARY_CLICKED: 60,
    AnnouncementEventType.PAGE_VIEWED: 60,
    AnnouncementEventType.PUSH_OPENED: 60,
}
# Used when settings define it (e.g. a separate Redis), otherwise the default cache.
DEDUPE_CACHE_ALIAS = 'announcement_dedupe'


def _text(value, max_length: int) -> str:
    return str(value).strip()[:max_length] if value is not None else ''


def _position(value) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if -32768 <= value <= 32767 else None


def _target(value) -> str:
    return value if value in AnnouncementEventTarget.values else ''


def _occurred_at(value):
    try:
        moment = parse_datetime(value) if isinstance(value, str) else None
    except ValueError:
        return None
    if moment is not None and timezone.is_naive(moment):
        moment = timezone.make_aware(moment, dt_timezone.utc)
    return moment


def _recent_enough(occurred_at, now) -> bool:
    return occurred_at is None or now - MAX_EVENT_AGE <= occurred_at <= now + MAX_CLOCK_SKEW


def _dedupe_cache():
    return caches[DEDUPE_CACHE_ALIAS if DEDUPE_CACHE_ALIAS in settings.CACHES else 'default']


def _first_in_window(announcement_id: int, device_id: str, event_type: str) -> bool:
    """True the first time this device reports this event in its window (atomic cache.add)."""
    device_hash = hashlib.sha256(device_id.encode('utf-8')).hexdigest()[:32]
    key = f'announcements:event:{event_type}:{announcement_id}:{device_hash}'
    return _dedupe_cache().add(key, 1, DEDUPE_SECONDS[event_type])


def _for_first_announcements(events):
    """Keeps the events of the first MAX_ANNOUNCEMENTS_PER_REQUEST distinct slugs."""
    kept_slugs = list(dict.fromkeys(event['slug'] for event in events))[:MAX_ANNOUNCEMENTS_PER_REQUEST]
    return [event for event in events if event['slug'] in kept_slugs]


def ingest(payload: dict, *, country: str = '', ip: Optional[str] = None) -> int:
    """Saves the valid events of one request and returns how many were accepted.

    Only the first MAX_EVENTS_PER_REQUEST events are read, for at most
    MAX_ANNOUNCEMENTS_PER_REQUEST announcements. Skipped: unknown types or slugs,
    an `at` more than 24 h old or more than 5 min ahead, and repeats from the
    same device (see the module docstring).
    """
    raw_events = payload.get('events')
    if not isinstance(raw_events, list):
        return 0

    candidates = _for_first_announcements([
        event for event in raw_events[:MAX_EVENTS_PER_REQUEST]
        if isinstance(event, dict) and event.get('type') in COUNTER_FIELD_BY_EVENT_TYPE
        and isinstance(event.get('slug'), str)
    ])
    ids_by_slug = dict(
        Announcement.objects.filter(slug__in={event['slug'] for event in candidates}).values_list('slug', 'id')
    )

    common = {
        'device_id': _text(payload.get('device_id'), 512),
        'platform': _text(payload.get('platform'), 32),
        'app_version': _text(payload.get('app_version'), 64),
        'locale': _text(payload.get('locale'), 64),
        'country': country,
        'ip': ip,
    }
    now = timezone.now()
    events, dismissals = [], []
    for event in candidates:
        announcement_id = ids_by_slug.get(event['slug'])
        occurred_at = _occurred_at(event.get('at'))
        if announcement_id is None or not _recent_enough(occurred_at, now):
            continue
        is_dismissal = event['type'] == AnnouncementEventType.DISMISSED
        if not is_dismissal and not _first_in_window(announcement_id, common['device_id'], event['type']):
            continue
        (dismissals if is_dismissal else events).append(AnnouncementEvent(
            announcement_id=announcement_id,
            type=event['type'],
            position=_position(event.get('position')),
            target=_target(event.get('target')),
            placement=_text(event.get('placement'), 16),
            station_slug=_text(event.get('station_slug'), 100),
            occurred_at=occurred_at,
            **common,
        ))
    if not events and not dismissals:
        return 0

    with transaction.atomic():
        saved = AnnouncementEvent.objects.bulk_create(events) + _save_new_dismissals(dismissals)
        _bump_counters(saved)
    return len(saved)


def _save_new_dismissals(dismissals):
    """Saves each close not already stored for its announcement and device.

    The partial unique constraint announcement_event_one_dismissal backs the
    check against concurrent requests.
    """
    if not dismissals:
        return []
    already_closed = set(
        AnnouncementEvent.objects.filter(
            type=AnnouncementEventType.DISMISSED, device_id=dismissals[0].device_id,
            announcement_id__in={dismissal.announcement_id for dismissal in dismissals},
        ).values_list('announcement_id', flat=True)
    )
    saved = []
    for dismissal in dismissals:
        if dismissal.announcement_id in already_closed:
            continue
        try:
            with transaction.atomic():
                dismissal.save()
        except IntegrityError:
            continue  # a concurrent request stored it first
        already_closed.add(dismissal.announcement_id)
        saved.append(dismissal)
    return saved


def _bump_counters(events):
    counts = Counter((event.announcement_id, event.type) for event in events)
    increments_by_announcement = {}
    for (announcement_id, event_type), count in counts.items():
        field = COUNTER_FIELD_BY_EVENT_TYPE[event_type]
        increments_by_announcement.setdefault(announcement_id, {})[field] = F(field) + count
    for announcement_id, increments in sorted(increments_by_announcement.items()):
        Announcement.objects.filter(pk=announcement_id).update(**increments)
