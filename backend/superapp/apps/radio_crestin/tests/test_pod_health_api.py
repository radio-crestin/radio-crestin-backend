"""POST /api/v1/pod-health/: a streaming pod reports whether its stream is up."""

import json
import os
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from superapp.apps.radio_crestin_scraping.scrapers.uptime import UptimeScraper

from ..models import (
    StationMetadataFetchCategories, Stations, StationsMetadataFetch, StationsUptime,
)
from .helpers import make_station

POD_KEY = 'test-pod-key'


@patch.dict(os.environ, {'STREAMING_POD_API_KEY': POD_KEY})
class PodHealthApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('station-a')

    def report(self, slug='station-a', **body):
        return self.client.post(
            '/api/v1/pod-health/', json.dumps({'station_slug': slug, **body}),
            content_type='application/json', HTTP_X_STREAMING_API_KEY=POD_KEY,
        )

    def test_first_report_creates_the_uptime_row_and_links_the_station(self):
        response = self.report(is_up=True, latency_ms=12)
        self.assertEqual(response.json(), {'success': True, 'config_version': 1})
        uptime = StationsUptime.objects.get(station=self.station)
        self.assertEqual((uptime.is_up, uptime.latency_ms), (True, 12))
        self.assertEqual(Stations.objects.get(id=self.station.id).latest_station_uptime_id, uptime.id)

    def test_later_reports_update_the_row_with_one_write(self):
        self.report(is_up=True)
        first = StationsUptime.objects.get(station=self.station)
        # the station lookup and the uptime update
        with self.assertNumQueries(2):
            self.report(is_up=False, latency_ms=0, reason='aac segments stale')
        uptime = StationsUptime.objects.get(station=self.station)
        self.assertEqual(uptime.id, first.id)
        self.assertFalse(uptime.is_up)
        self.assertEqual(uptime.raw_data['reason'], 'aac segments stale')
        self.assertGreater(uptime.timestamp, first.timestamp)
        self.assertGreater(uptime.updated_at, first.updated_at)

    def test_the_answer_carries_the_config_version_an_admin_change_bumps(self):
        before = self.report(is_up=True).json()['config_version']
        category = StationMetadataFetchCategories.objects.create(slug='shoutcast')
        fetcher = StationsMetadataFetch.objects.create(
            station=self.station, station_metadata_fetch_category=category,
            url='https://example.com/stats')
        added = self.report(is_up=True).json()['config_version']
        fetcher.delete()
        removed = self.report(is_up=True).json()['config_version']
        self.assertGreater(added, before)
        self.assertGreater(removed, added)

    def test_unknown_station_and_wrong_key(self):
        self.assertEqual(self.report(slug='no-such-station').status_code, 404)
        response = self.client.post(
            '/api/v1/pod-health/', json.dumps({'station_slug': 'station-a'}),
            content_type='application/json', HTTP_X_STREAMING_API_KEY='wrong',
        )
        self.assertEqual(response.status_code, 401)


class PodHealthWithoutKeyTests(TestCase):
    """An unset STREAMING_POD_API_KEY used to fall back to a default key
    ('dev-streaming-key') here; now it refuses everyone."""

    def test_unset_key_refuses_the_old_default(self):
        make_station('station-a')
        env = {k: v for k, v in os.environ.items() if k != 'STREAMING_POD_API_KEY'}
        with patch.dict(os.environ, env, clear=True):
            response = self.client.post(
                '/api/v1/pod-health/', json.dumps({'station_slug': 'station-a'}),
                content_type='application/json', HTTP_X_STREAMING_API_KEY='dev-streaming-key',
            )
        self.assertEqual(response.status_code, 401)


class ScheduledUptimeCheckTests(TestCase):
    """The 5-minute HTTP check leaves a station to its streaming pod while the
    pod's report is fresh: pods send a heartbeat only every 60 s, so an
    overwritten verdict would otherwise stay up to a minute."""

    def setUp(self):
        self.station = make_station('station-a')

    @patch.dict(os.environ, {'STREAMING_POD_API_KEY': POD_KEY})
    def pod_reports(self, is_up):
        self.client.post(
            '/api/v1/pod-health/', json.dumps({'station_slug': 'station-a', 'is_up': is_up}),
            content_type='application/json', HTTP_X_STREAMING_API_KEY=POD_KEY,
        )

    def check_all(self, upstream_up):
        with patch.object(UptimeScraper, '_check_stream_response',
                          return_value={'success': upstream_up, 'status_code': 200}):
            return UptimeScraper().check_all_stations_uptime()

    def test_a_fresh_pod_report_is_left_alone(self):
        self.pod_reports(is_up=True)
        summary = self.check_all(upstream_up=False)
        self.assertEqual((summary['total_checked'], summary['left_to_pods']), (0, 1))
        self.assertTrue(StationsUptime.objects.get(station=self.station).is_up)

    def test_a_pod_silent_for_minutes_is_checked_again(self):
        self.pod_reports(is_up=True)
        StationsUptime.objects.update(timestamp=timezone.now() - timedelta(minutes=4))
        summary = self.check_all(upstream_up=False)
        self.assertEqual(summary['total_checked'], 1)
        self.assertFalse(StationsUptime.objects.get(station=self.station).is_up)

    def test_a_station_without_a_pod_is_checked(self):
        self.check_all(upstream_up=False)
        uptime = StationsUptime.objects.get(station=self.station)
        self.assertFalse(uptime.is_up)
        # and its own result is not mistaken for a pod's next time
        self.check_all(upstream_up=True)
        self.assertTrue(StationsUptime.objects.get(station=self.station).is_up)
