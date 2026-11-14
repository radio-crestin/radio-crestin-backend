"""Admin numbers for announcements, counted per unique device so one noisy device can't move them.

They come from the raw events, which are kept 180 days; the plain totals on the
announcement are kept forever.
"""
from datetime import datetime, time, timedelta
from typing import Optional

from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.utils import timezone

from ..models import AnnouncementEvent, AnnouncementEventType, AnnouncementStatBucket, StatGranularity
from .announcement_stat_buckets import DAY_TIME_ZONE, bucket_start


def history(announcement, days: int = 30, hours: int = 48, now: Optional[datetime] = None) -> dict:
    """The last `days` Bucharest days and `hours` hours as buckets, oldest first, with empty ones filled in.

    Two queries, both on the bucket table.
    """
    now = now or timezone.now()
    today = now.astimezone(DAY_TIME_ZONE).date()
    day_starts = [datetime.combine(today - timedelta(days=back), time(), DAY_TIME_ZONE) for back in range(days - 1, -1, -1)]
    this_hour = bucket_start(StatGranularity.HOUR, now)
    hour_starts = [this_hour - timedelta(hours=back) for back in range(hours - 1, -1, -1)]
    return {
        'days': _buckets(announcement, StatGranularity.DAY, day_starts),
        'hours': _buckets(announcement, StatGranularity.HOUR, hour_starts),
    }


def _buckets(announcement, granularity: str, starts: list) -> list:
    stored = {
        bucket.bucket_start: bucket
        for bucket in AnnouncementStatBucket.objects.filter(
            announcement=announcement, granularity=granularity,
            bucket_start__gte=starts[0], bucket_start__lte=starts[-1],
        )
    }
    return [stored.get(start) or AnnouncementStatBucket(granularity=granularity, bucket_start=start) for start in starts]


def _unique_devices_subquery(event_type: str):
    devices = (
        AnnouncementEvent.objects
        .filter(announcement=OuterRef('pk'), type=event_type)
        .order_by()
        .values('announcement')
        .annotate(devices=Count('device_id', distinct=True))
        .values('devices')
    )
    return Subquery(devices, output_field=IntegerField())


def with_unique_counts(queryset):
    """Adds unique_viewers and unique_clickers to each announcement (for the list page)."""
    return queryset.annotate(
        unique_viewers=_unique_devices_subquery(AnnouncementEventType.IMPRESSION),
        unique_clickers=_unique_devices_subquery(AnnouncementEventType.CLICKED),
    )


def click_rate(unique_clickers: Optional[int], unique_viewers: Optional[int]) -> Optional[float]:
    """Unique clickers / unique viewers, or None without viewers."""
    if not unique_viewers:
        return None
    return (unique_clickers or 0) / unique_viewers


def summary(announcement) -> dict:
    """Headline numbers and breakdowns for one announcement's change page."""
    events = AnnouncementEvent.objects.filter(announcement=announcement).order_by()
    unique_by_type = dict(events.values_list('type').annotate(devices=Count('device_id', distinct=True)))
    unique_viewers = unique_by_type.get(AnnouncementEventType.IMPRESSION, 0)
    unique_clickers = unique_by_type.get(AnnouncementEventType.CLICKED, 0)
    return {
        'unique_viewers': unique_viewers,
        'unique_clickers': unique_clickers,
        'unique_closers': unique_by_type.get(AnnouncementEventType.DISMISSED, 0),
        'unique_page_viewers': unique_by_type.get(AnnouncementEventType.PAGE_VIEWED, 0),
        'unique_push_openers': unique_by_type.get(AnnouncementEventType.PUSH_OPENED, 0),
        'click_rate': click_rate(unique_clickers, unique_viewers),
        **_breakdowns(events),
    }


def _breakdowns(events) -> dict:
    """Events per type and platform, and clicks per tapped target, from one grouped query."""
    by_type_and_platform, clicks_by_target = {}, {}
    rows = events.values_list('type', 'platform', 'target').annotate(n=Count('*'))
    for event_type, platform, target, count in rows:
        key = (event_type, platform)
        by_type_and_platform[key] = by_type_and_platform.get(key, 0) + count
        if event_type == AnnouncementEventType.CLICKED:
            clicks_by_target[target] = clicks_by_target.get(target, 0) + count
    return {
        'by_type_and_platform': [
            {'type': event_type, 'platform': platform, 'events': count}
            for (event_type, platform), count in sorted(by_type_and_platform.items())
        ],
        'clicks_by_target': clicks_by_target,
    }
