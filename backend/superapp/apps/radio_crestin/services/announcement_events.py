"""Stores the events clients report and bumps the totals on each announcement."""
from collections import Counter
from datetime import timezone as dt_timezone
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import Announcement, AnnouncementEvent, AnnouncementEventTarget
from ..models.announcement_events import COUNTER_FIELD_BY_EVENT_TYPE

MAX_EVENTS_PER_REQUEST = 100


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


def ingest(payload: dict, *, country: str = '', ip: Optional[str] = None) -> int:
    """Saves the valid events of one request and returns how many were accepted.

    Only the first MAX_EVENTS_PER_REQUEST events are read. Events with an unknown
    type or an unknown slug are skipped.
    """
    raw_events = payload.get('events')
    if not isinstance(raw_events, list):
        return 0

    candidates = [
        event for event in raw_events[:MAX_EVENTS_PER_REQUEST]
        if isinstance(event, dict) and event.get('type') in COUNTER_FIELD_BY_EVENT_TYPE
        and isinstance(event.get('slug'), str)
    ]
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
    events = [
        AnnouncementEvent(
            announcement_id=ids_by_slug[event['slug']],
            type=event['type'],
            position=_position(event.get('position')),
            target=_target(event.get('target')),
            placement=_text(event.get('placement'), 16),
            station_slug=_text(event.get('station_slug'), 100),
            occurred_at=_occurred_at(event.get('at')),
            **common,
        )
        for event in candidates if event['slug'] in ids_by_slug
    ]
    if not events:
        return 0

    with transaction.atomic():
        AnnouncementEvent.objects.bulk_create(events)
        _bump_counters(events)
    return len(events)


def _bump_counters(events):
    counts = Counter((event.announcement_id, event.type) for event in events)
    increments_by_announcement = {}
    for (announcement_id, event_type), count in counts.items():
        field = COUNTER_FIELD_BY_EVENT_TYPE[event_type]
        increments_by_announcement.setdefault(announcement_id, {})[field] = F(field) + count
    for announcement_id, increments in sorted(increments_by_announcement.items()):
        Announcement.objects.filter(pk=announcement_id).update(**increments)
