"""Hourly and daily history of each announcement's events (AnnouncementStatBucket).

A bucket holds absolute counts recomputed from the raw events with one grouped query per
granularity, then upserted. Recomputing a bucket twice gives the same row, so a missed or
repeated run heals itself, and a day's unique devices are counted over the whole day
instead of summed from its hours.

upsert_recent() runs every few minutes (tasks/update_announcement_stat_buckets.py): it
recomputes the hours and days that got events since the last run. upsert_all() rebuilds
everything the raw events still cover (the backfill command, and the first run).
"""
from datetime import datetime, time, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db.models import Count, Max, Min, Q
from django.db.models.functions import TruncDay, TruncHour
from django.utils import timezone

from ..models import (
    AnnouncementEvent, AnnouncementEventType, AnnouncementSettings, AnnouncementStatBucket, StatGranularity,
)
from ..models.announcement_events import COUNTER_FIELD_BY_EVENT_TYPE, RETENTION_DAYS

# Days are calendar days where the listeners are.
DAY_TIME_ZONE = ZoneInfo('Europe/Bucharest')
# Re-reads events received this long before the last run, for requests that committed late.
OVERLAP = timedelta(minutes=5)
COUNT_FIELDS = [
    *COUNTER_FIELD_BY_EVENT_TYPE.values(), 'unique_viewers', 'unique_clickers',
]
UNIQUE_FIELDS = ['announcement', 'granularity', 'bucket_start']


def bucket_start(granularity: str, moment: datetime) -> datetime:
    """The start of the hour (UTC) or the Bucharest day that holds this moment."""
    if granularity == StatGranularity.HOUR:
        return moment.astimezone(dt_timezone.utc).replace(minute=0, second=0, microsecond=0)
    return datetime.combine(moment.astimezone(DAY_TIME_ZONE).date(), time(), DAY_TIME_ZONE)


def bucket_end(granularity: str, start: datetime) -> datetime:
    """The start of the next bucket (a Bucharest day is 23 or 25 hours long when the clocks change)."""
    if granularity == StatGranularity.HOUR:
        return start + timedelta(hours=1)
    return datetime.combine(start.astimezone(DAY_TIME_ZONE).date() + timedelta(days=1), time(), DAY_TIME_ZONE)


def _truncate(granularity: str):
    if granularity == StatGranularity.HOUR:
        return TruncHour('created_at', tzinfo=dt_timezone.utc)
    return TruncDay('created_at', tzinfo=DAY_TIME_ZONE)


def _counts():
    counts = {field: Count('pk', filter=Q(type=event_type)) for event_type, field in COUNTER_FIELD_BY_EVENT_TYPE.items()}
    counts['unique_viewers'] = Count('device_id', distinct=True, filter=Q(type=AnnouncementEventType.IMPRESSION))
    counts['unique_clickers'] = Count('device_id', distinct=True, filter=Q(type=AnnouncementEventType.CLICKED))
    return counts


def bucket_rows(granularity: str, ranges: dict):
    """One grouped query: the counts of every bucket inside {announcement_id: (start, end)}.

    It reads the events through the (announcement, created_at) index, or the created_at
    index when most announcements are in it.
    """
    window = Q()
    for announcement_id, (start, end) in ranges.items():
        window |= Q(announcement_id=announcement_id, created_at__gte=start, created_at__lt=end)
    return (
        AnnouncementEvent.objects.filter(window).order_by()
        .annotate(bucket_start=_truncate(granularity))
        .values('announcement_id', 'bucket_start')
        .annotate(**_counts())
    )


def upsert(granularity: str, ranges: dict) -> int:
    """Recomputes the buckets inside the ranges (bucket-aligned) and writes them in one upsert."""
    if not ranges:
        return 0
    buckets = [AnnouncementStatBucket(granularity=granularity, **row) for row in bucket_rows(granularity, ranges)]
    AnnouncementStatBucket.objects.bulk_create(
        buckets, batch_size=1000, update_conflicts=True, unique_fields=UNIQUE_FIELDS, update_fields=COUNT_FIELDS,
    )
    return len(buckets)


def upsert_touched_since(since: datetime) -> int:
    """Recomputes every hour and day that got an event received at or after `since`."""
    touched = (
        AnnouncementEvent.objects.filter(created_at__gte=since).order_by()
        .values('announcement_id')
        .annotate(first=Min('created_at'), last=Max('created_at'))
    )
    written = 0
    for granularity in (StatGranularity.HOUR, StatGranularity.DAY):
        ranges = {
            row['announcement_id']: (bucket_start(granularity, row['first']),
                                     bucket_end(granularity, bucket_start(granularity, row['last'])))
            for row in touched
        }
        written += upsert(granularity, ranges)
    return written


def upsert_all() -> int:
    """Rebuilds the buckets of every announcement from the events still kept.

    Buckets that start before the retention cutoff may have lost events to it, so they keep
    the counts they were given while the events were all there.
    """
    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    spans = (
        AnnouncementEvent.objects.order_by().values('announcement_id')
        .annotate(first=Min('created_at'), last=Max('created_at'))
    )
    written = 0
    for span in spans:
        for granularity in (StatGranularity.HOUR, StatGranularity.DAY):
            start = bucket_start(granularity, max(span['first'], cutoff))
            if start < cutoff:
                start = bucket_end(granularity, start)
            end = bucket_end(granularity, bucket_start(granularity, span['last']))
            if start < end:
                written += upsert(granularity, {span['announcement_id']: (start, end)})
    return written


def _mark_updated_until(settings: AnnouncementSettings, moment: datetime):
    # Only forward: a slower run that started earlier must not move it back.
    (AnnouncementSettings.objects.filter(pk=settings.pk)
     .filter(Q(stats_updated_until__isnull=True) | Q(stats_updated_until__lt=moment))
     .update(stats_updated_until=moment))


def upsert_recent() -> dict:
    """The periodic run: the buckets touched since the last run, or everything on the first run."""
    started = timezone.now()
    settings = AnnouncementSettings.load()
    if settings.stats_updated_until is None:
        written = upsert_all()
    else:
        written = upsert_touched_since(settings.stats_updated_until - OVERLAP)
    _mark_updated_until(settings, started)
    return {'buckets': written, 'updated_until': started.isoformat()}


def rebuild() -> int:
    """The backfill: everything, then the watermark, so the periodic run carries on from here."""
    started = timezone.now()
    written = upsert_all()
    _mark_updated_until(AnnouncementSettings.load(), started)
    return written
