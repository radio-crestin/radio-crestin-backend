import io
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from ..models import Announcement, AnnouncementEvent, AnnouncementSettings, AnnouncementStatBucket, StatGranularity
from ..services import announcement_stat_buckets as buckets

UTC = dt_timezone.utc
LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class BucketTestCase(TestCase):
    now = at('2026-11-13T12:00:00')

    def setUp(self):
        self.announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')
        self.other = Announcement.objects.create(slug='another-announcement', title='x')
        clock = patch('superapp.apps.radio_crestin.services.announcement_stat_buckets.timezone.now',
                      side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def event(self, when, kind='impression', device='phone-1', announcement=None):
        event = AnnouncementEvent.objects.create(
            announcement=announcement or self.announcement, type=kind, device_id=device, platform='android')
        AnnouncementEvent.objects.filter(pk=event.pk).update(created_at=at(when))  # auto_now_add ignores a given time
        return event

    def bucket(self, granularity, start, announcement=None):
        return AnnouncementStatBucket.objects.get(
            announcement=announcement or self.announcement, granularity=granularity, bucket_start=at(start))


class RecomputeTests(BucketTestCase):
    def test_counts_every_type_and_unique_devices(self):
        for device in ('a', 'a', 'b', 'c'):
            self.event('2026-11-12T10:15:00', 'impression', device)
        self.event('2026-11-12T10:20:00', 'clicked', 'a')
        self.event('2026-11-12T10:21:00', 'clicked', 'a')
        self.event('2026-11-12T10:30:00', 'secondary_clicked', 'b')
        self.event('2026-11-12T10:31:00', 'dismissed', 'c')
        self.event('2026-11-12T10:32:00', 'page_viewed', 'a')
        self.event('2026-11-12T10:33:00', 'push_opened', 'a')
        self.event('2026-11-12T10:34:00', 'video_play', 'a')
        self.event('2026-11-12T13:00:00', 'impression', 'a')
        self.event('2026-11-12T10:15:00', 'impression', 'z', announcement=self.other)

        buckets.upsert_all()

        hour = self.bucket(StatGranularity.HOUR, '2026-11-12T10:00:00')
        self.assertEqual(
            (hour.impressions, hour.clicks, hour.secondary_clicks, hour.dismissals, hour.page_views,
             hour.push_opens, hour.video_plays, hour.unique_viewers, hour.unique_clickers),
            (4, 2, 1, 1, 1, 1, 1, 3, 1),
        )
        self.assertEqual(self.bucket(StatGranularity.HOUR, '2026-11-12T13:00:00').impressions, 1)
        # 12 Nov in Bucharest (UTC+2 in November) starts at 22:00 UTC the day before.
        day = self.bucket(StatGranularity.DAY, '2026-11-11T22:00:00')
        self.assertEqual((day.impressions, day.unique_viewers), (5, 3))  # 'a' twice in the day, counted once
        self.assertEqual(self.bucket(StatGranularity.DAY, '2026-11-11T22:00:00', self.other).impressions, 1)
        self.assertEqual(AnnouncementStatBucket.objects.count(), 5)

    def test_idempotent_and_absolute(self):
        self.event('2026-11-12T10:15:00', device='a')
        buckets.upsert_all()
        buckets.upsert_all()
        self.assertEqual(self.bucket(StatGranularity.HOUR, '2026-11-12T10:00:00').impressions, 1)

        self.event('2026-11-12T10:40:00', device='b')
        buckets.upsert_all()
        hour = self.bucket(StatGranularity.HOUR, '2026-11-12T10:00:00')
        self.assertEqual((hour.impressions, hour.unique_viewers), (2, 2))
        self.assertEqual(AnnouncementStatBucket.objects.count(), 2)

    def test_skips_buckets_cut_by_the_event_retention(self):
        self.now = at('2026-11-13T12:30:00')
        cutoff = self.now - timedelta(days=buckets.RETENTION_DAYS)  # 2026-05-17T12:30Z
        self.event((cutoff + timedelta(minutes=10)).replace(tzinfo=None).isoformat())  # its hour and day began before it
        self.event((cutoff + timedelta(hours=1)).replace(tzinfo=None).isoformat())
        buckets.upsert_all()
        self.assertEqual(
            list(AnnouncementStatBucket.objects.values_list('granularity', 'bucket_start')),
            [(StatGranularity.HOUR, at('2026-05-17T13:00:00'))],
        )


class BucharestDayTests(BucketTestCase):
    now = at('2026-11-13T12:00:00')

    def test_spring_forward_day_is_23_hours(self):
        self.now = at('2026-04-10T12:00:00')
        self.event('2026-03-28T21:59:00', device='before-midnight')  # 23:59 on 28 Mar (UTC+2)
        self.event('2026-03-28T22:00:00', device='midnight')  # 00:00 on 29 Mar
        self.event('2026-03-29T20:59:00', device='last-minute')  # 23:59 on 29 Mar (UTC+3 since 03:00)
        self.event('2026-03-29T21:00:00', device='next-day')  # 00:00 on 30 Mar
        buckets.upsert_all()
        days = dict(AnnouncementStatBucket.objects.filter(granularity=StatGranularity.DAY)
                    .values_list('bucket_start', 'impressions'))
        self.assertEqual(days, {
            at('2026-03-27T22:00:00'): 1, at('2026-03-28T22:00:00'): 2, at('2026-03-29T21:00:00'): 1,
        })
        start = at('2026-03-28T22:00:00')
        self.assertEqual(buckets.bucket_end(StatGranularity.DAY, start) - start, timedelta(hours=23))

    def test_fall_back_day_is_25_hours(self):
        self.event('2026-10-24T21:00:00', device='midnight')  # 00:00 on 25 Oct (UTC+3)
        self.event('2026-10-25T21:59:00', device='last-minute')  # 23:59 on 25 Oct (UTC+2 since 04:00)
        self.event('2026-10-25T22:00:00', device='next-day')
        buckets.upsert_all()
        days = dict(AnnouncementStatBucket.objects.filter(granularity=StatGranularity.DAY)
                    .values_list('bucket_start', 'impressions'))
        self.assertEqual(days, {at('2026-10-24T21:00:00'): 2, at('2026-10-25T22:00:00'): 1})
        start = at('2026-10-24T21:00:00')
        self.assertEqual(buckets.bucket_end(StatGranularity.DAY, start) - start, timedelta(hours=25))


class PeriodicRunTests(BucketTestCase):
    def watermark(self):
        return AnnouncementSettings.load().stats_updated_until

    def test_first_run_rebuilds_everything_then_sets_the_watermark(self):
        self.event('2026-10-01T08:00:00')
        result = buckets.upsert_recent()
        self.assertEqual(result['buckets'], 2)
        self.assertEqual(self.watermark(), self.now)

    def test_rereads_late_commits_inside_the_overlap_only(self):
        buckets.upsert_recent()  # sets the watermark to now
        self.now += timedelta(minutes=5)
        self.event('2026-11-13T11:57:00', device='late')  # received before the last run, committed after it
        self.event('2026-11-13T11:50:00', device='too-late')  # older than the overlap: left for the next rebuild
        self.event('2026-11-13T12:03:00', device='new')
        buckets.upsert_recent()
        hour = self.bucket(StatGranularity.HOUR, '2026-11-13T11:00:00')
        # The 11:00 hour is recomputed whole (absolute counts), so the older event is in it too.
        self.assertEqual(hour.impressions, 2)
        self.assertEqual(self.bucket(StatGranularity.HOUR, '2026-11-13T12:00:00').impressions, 1)
        self.assertEqual(self.watermark(), self.now)

    def test_untouched_buckets_are_left_alone(self):
        self.event('2026-11-13T09:10:00', device='a')
        buckets.upsert_recent()
        AnnouncementStatBucket.objects.filter(bucket_start=at('2026-11-13T09:00:00')).update(impressions=99)
        self.now += timedelta(minutes=5)
        self.event('2026-11-13T12:02:00', device='b')
        buckets.upsert_recent()
        self.assertEqual(self.bucket(StatGranularity.HOUR, '2026-11-13T09:00:00').impressions, 99)
        day = self.bucket(StatGranularity.DAY, '2026-11-12T22:00:00')
        self.assertEqual(day.impressions, 2)  # the day is touched, so it is recomputed from the events

    def test_watermark_only_moves_forward(self):
        buckets.upsert_recent()
        self.now -= timedelta(minutes=10)  # a slower run that started earlier finishes later
        buckets.upsert_recent()
        self.assertEqual(self.watermark(), self.now + timedelta(minutes=10))

    def test_task(self):
        from ..tasks.update_announcement_stat_buckets import update_announcement_stat_buckets
        self.event('2026-11-13T11:00:00')
        self.assertEqual(update_announcement_stat_buckets()['buckets'], 2)

    def test_backfill_command(self):
        self.event('2026-09-01T08:00:00')
        self.event('2026-11-01T08:00:00')
        out = io.StringIO()
        call_command('backfill_announcement_stats', stdout=out)
        self.assertIn('4 buckets written', out.getvalue())
        self.assertEqual(self.watermark(), self.now)

    def test_query_plan_uses_an_events_index(self):
        start = at('2026-11-13T00:00:00')
        rows = buckets.bucket_rows(StatGranularity.DAY, {self.announcement.pk: (start, start + timedelta(days=1))})
        with connection.cursor() as cursor:
            # A test table is tiny, so the planner would read it whole; ask whether an index serves the query.
            cursor.execute('SET LOCAL enable_seqscan = off')
        plan = rows.explain()
        self.assertNotIn('Seq Scan', plan)
        self.assertIn('Index Cond: (announcement_id = ', plan)
