import csv
import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ..models import AnnouncementStatBucket, StatGranularity
from ..services import announcement_stats
from .test_announcement_stat_buckets import LOCMEM_CACHE, BucketTestCase, at


@override_settings(CACHES=LOCMEM_CACHE)
class HistoryAdminTests(BucketTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))

    def test_history_reads_two_queries_and_fills_empty_buckets(self):
        AnnouncementStatBucket.objects.create(announcement=self.announcement, granularity=StatGranularity.HOUR,
                                              bucket_start=at('2026-11-13T11:00:00'), impressions=7)
        AnnouncementStatBucket.objects.create(announcement=self.announcement, granularity=StatGranularity.DAY,
                                              bucket_start=at('2026-11-12T22:00:00'), impressions=9)
        with self.assertNumQueries(2):
            history = announcement_stats.history(self.announcement, now=self.now)
        self.assertEqual(len(history['days']), 30)
        self.assertEqual(len(history['hours']), 48)
        self.assertEqual(history['days'][-1].impressions, 9)
        self.assertEqual(history['hours'][-2].impressions, 7)
        self.assertEqual(history['hours'][0].impressions, 0)

    def test_change_page_shows_history_without_growing_queries(self):
        url = reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,))
        self.client.get(url)
        with CaptureQueriesContext(connection) as before:
            response = self.client.get(url)
        self.assertContains(response, 'class="chart"', count=2)
        AnnouncementStatBucket.objects.bulk_create([
            AnnouncementStatBucket(announcement=self.announcement, granularity=StatGranularity.HOUR,
                                   bucket_start=self.now - timedelta(hours=index), impressions=index)
            for index in range(200)
        ])
        with self.assertNumQueries(len(before)):
            self.client.get(url)
        self.assertFalse([q for q in before if 'FROM "announcement_stat_buckets"' in q['sql']
                          and 'announcement_events' in q['sql']])

    def test_csv_download(self):
        AnnouncementStatBucket.objects.create(announcement=self.announcement, granularity=StatGranularity.DAY,
                                              bucket_start=at('2026-11-12T22:00:00'), impressions=9, clicks=2)
        url = reverse('admin:radio_crestin_announcement_history_csv', args=(self.announcement.pk,))
        response = self.client.get(url, {'granularity': 'day'})
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertEqual(rows[0][:4], ['start_bucharest', 'start_utc', 'impressions', 'clicks'])
        self.assertEqual(rows[1][:4], ['2026-11-13T00:00:00+02:00', '2026-11-12T22:00:00+00:00', '9', '2'])
        self.assertEqual(len(list(csv.reader(io.StringIO(self.client.get(url, {'granularity': 'hour'})
                                                         .content.decode())))), 1)

    def test_csv_needs_view_permission(self):
        staff = get_user_model().objects.create_user(email='staff@example.com', password='x')
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        url = reverse('admin:radio_crestin_announcement_history_csv', args=(self.announcement.pk,))
        self.assertEqual(self.client.get(url).status_code, 403)
