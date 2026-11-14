"""POST /api/v1/pod-health/: a streaming pod reports whether its stream is up."""

import json
import os
from unittest.mock import patch

from django.test import TestCase

from ..models import Stations, StationsUptime
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
        self.assertEqual(response.json(), {'success': True})
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

    def test_unknown_station_and_wrong_key(self):
        self.assertEqual(self.report(slug='no-such-station').status_code, 404)
        response = self.client.post(
            '/api/v1/pod-health/', json.dumps({'station_slug': 'station-a'}),
            content_type='application/json', HTTP_X_STREAMING_API_KEY='wrong',
        )
        self.assertEqual(response.status_code, 401)
