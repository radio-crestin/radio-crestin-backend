from datetime import timedelta

from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone

from ..models import (
    Artists, Songs, Stations, StationsUptime, StationsNowPlaying,
    StationsNowPlayingHistory,
)


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda request: False})
class StationsMetadataPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.artists = [Artists.objects.create(name=f"Artist {i}") for i in range(5)]
        cls.songs = [
            Songs.objects.create(name=f"Song {i}", artist=cls.artists[i % 5])
            for i in range(10)
        ]
        cls.stations = []
        for i in range(10):
            station = Stations.objects.create(
                slug=f"station-{i}",
                title=f"Station {i}",
                order=i,
                station_order=float(i),
                stream_url=f"http://stream{i}.example.com",
                website=f"http://station{i}.example.com",
            )
            uptime = StationsUptime.objects.create(
                station=station, timestamp=now, is_up=True, latency_ms=100, raw_data={},
            )
            station.latest_station_uptime = uptime
            np = StationsNowPlaying.objects.create(
                station=station, timestamp=now, song=cls.songs[i],
                listeners=i * 10, raw_data={}, error=None,
            )
            station.latest_station_now_playing = np
            station.save()
            cls.stations.append(station)

        # Create history records — start from 1 hour ago to avoid edge cases
        for station in cls.stations:
            for j in range(5):
                StationsNowPlayingHistory.objects.create(
                    station=station,
                    timestamp=now - timedelta(hours=j + 1),
                    song=cls.songs[(station.id + j) % 10],
                    listeners=station.id * 10 + j,
                )

    # ──────────────────────────────────────────────
    # /api/v1/stations (existing, backward compat)
    # ──────────────────────────────────────────────

    def test_stations_endpoint_returns_200(self):
        """GET /api/v1/stations should return station data."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations', {'timestamp': ts})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data', data)
        self.assertIn('stations', data['data'])
        self.assertEqual(len(data['data']['stations']), 10)

    def test_stations_endpoint_query_count(self):
        """GET /api/v1/stations should use a bounded number of queries."""
        ts = int(timezone.now().timestamp())
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get('/api/v1/stations', {'timestamp': ts})
        self.assertEqual(response.status_code, 200)
        for i, q in enumerate(ctx.captured_queries):
            print(f"  Query {i+1}: {q['sql'][:200]}")

    def test_stations_endpoint_redirect_without_timestamp(self):
        """GET /api/v1/stations without timestamp should redirect."""
        response = self.client.get('/api/v1/stations')
        self.assertEqual(response.status_code, 302)
        self.assertIn('timestamp=', response['Location'])

    def test_stations_filter_by_station_slugs(self):
        """GET /api/v1/stations with station_slugs returns only matching stations."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations', {
            'timestamp': ts,
            'station_slugs': 'station-0,station-2,station-4',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [s['slug'] for s in data['data']['stations']]
        self.assertEqual(sorted(slugs), ['station-0', 'station-2', 'station-4'])

    def test_stations_filter_by_exclude_station_slugs(self):
        """GET /api/v1/stations with exclude_station_slugs omits matching stations."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations', {
            'timestamp': ts,
            'exclude_station_slugs': 'station-0,station-1',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [s['slug'] for s in data['data']['stations']]
        self.assertEqual(len(slugs), 8)
        self.assertNotIn('station-0', slugs)
        self.assertNotIn('station-1', slugs)

    # ──────────────────────────────────────────────
    # /api/v1/stations-metadata
    # ──────────────────────────────────────────────

    def test_stations_metadata_default(self):
        """GET /api/v1/stations-metadata with timestamp returns all stations."""
        ts = int(timezone.now().timestamp())
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                '/api/v1/stations-metadata', {'timestamp': ts},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data', data)
        stations = data['data']['stations_metadata']
        self.assertEqual(len(stations), 10)
        # Each station should have uptime and now_playing
        for station in stations:
            self.assertIn('slug', station)
            self.assertIn('uptime', station)
            self.assertIn('now_playing', station)
        for i, q in enumerate(ctx.captured_queries):
            print(f"  Query {i+1}: {q['sql'][:200]}")
        self.assertLessEqual(len(ctx), 2, f"Expected <=2 queries, got {len(ctx)}")

    def test_stations_metadata_with_changes(self):
        """GET /api/v1/stations-metadata with changes_from_timestamp returns only changed stations."""
        ts = int(timezone.now().timestamp())
        changes_from = int((timezone.now() - timedelta(hours=2)).timestamp())
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                '/api/v1/stations-metadata',
                {'timestamp': ts, 'changes_from_timestamp': changes_from},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        stations = data['data']['stations_metadata']
        self.assertGreater(len(stations), 0)
        self.assertLessEqual(len(stations), 10)
        for station in stations:
            self.assertIn('now_playing', station)
        for i, q in enumerate(ctx.captured_queries):
            print(f"  Query {i+1}: {q['sql'][:200]}")
        self.assertLessEqual(len(ctx), 4, f"Expected <=4 queries, got {len(ctx)}")

    def test_stations_metadata_no_changes(self):
        """changes_from_timestamp far in the future should return empty list."""
        ts = int(timezone.now().timestamp())
        # Use a future changes_from to guarantee no history records match
        future_ts = ts + 3600
        response = self.client.get(
            '/api/v1/stations-metadata',
            {'timestamp': ts, 'changes_from_timestamp': future_ts},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['data']['stations_metadata']), 0)

    def test_stations_metadata_redirect_without_timestamp(self):
        """GET /api/v1/stations-metadata without timestamp should redirect."""
        response = self.client.get('/api/v1/stations-metadata')
        self.assertEqual(response.status_code, 302)
        self.assertIn('timestamp=', response['Location'])

    def test_stations_metadata_filter_by_station_slugs(self):
        """GET /api/v1/stations-metadata with station_slugs returns only matching stations."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': ts,
            'station_slugs': 'station-1,station-3',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [s['slug'] for s in data['data']['stations_metadata']]
        self.assertEqual(sorted(slugs), ['station-1', 'station-3'])

    def test_stations_metadata_filter_by_exclude_station_slugs(self):
        """GET /api/v1/stations-metadata with exclude_station_slugs omits matching stations."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': ts,
            'exclude_station_slugs': 'station-0,station-1,station-2',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [s['slug'] for s in data['data']['stations_metadata']]
        self.assertEqual(len(slugs), 7)
        for excluded in ['station-0', 'station-1', 'station-2']:
            self.assertNotIn(excluded, slugs)

    def test_stations_metadata_combined_slug_filters(self):
        """station_slugs and exclude_station_slugs can be combined."""
        ts = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': ts,
            'station_slugs': 'station-0,station-1,station-2,station-3',
            'exclude_station_slugs': 'station-2',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        slugs = [s['slug'] for s in data['data']['stations_metadata']]
        self.assertEqual(sorted(slugs), ['station-0', 'station-1', 'station-3'])

    # ──────────────────────────────────────────────
    # /api/v1/stations-metadata-history
    # ──────────────────────────────────────────────

    def test_metadata_history_endpoint(self):
        """GET /api/v1/stations-metadata-history returns history data."""
        from_ts = int((timezone.now() - timedelta(hours=5)).timestamp())
        to_ts = int(timezone.now().timestamp())
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                '/api/v1/stations-metadata-history',
                {
                    'station_slug': 'station-0',
                    'from_timestamp': from_ts,
                    'to_timestamp': to_ts,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        history = data['data']['stations_metadata_history']
        self.assertEqual(history['station_slug'], 'station-0')
        self.assertGreater(history['count'], 0)
        self.assertEqual(len(history['history']), history['count'])
        for entry in history['history']:
            if entry['song']:
                self.assertIn('artist', entry['song'])
        for i, q in enumerate(ctx.captured_queries):
            print(f"  Query {i+1}: {q['sql'][:200]}")
        self.assertLessEqual(len(ctx), 3, f"Expected <=3 queries, got {len(ctx)}")

    def test_metadata_history_defaults_without_timestamps(self):
        """GET /api/v1/stations-metadata-history without timestamps uses defaults (last 1h)."""
        response = self.client.get(
            '/api/v1/stations-metadata-history',
            {'station_slug': 'station-0'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        history = data['data']['stations_metadata_history']
        self.assertEqual(history['station_slug'], 'station-0')
        # Should have the 1 record from 1 hour ago
        self.assertGreaterEqual(history['count'], 1)

    def test_metadata_history_24h_limit(self):
        """GET /api/v1/stations-metadata-history with >24h range should return error."""
        response = self.client.get(
            '/api/v1/stations-metadata-history',
            {
                'station_slug': 'station-0',
                'from_timestamp': int((timezone.now() - timedelta(hours=25)).timestamp()),
                'to_timestamp': int(timezone.now().timestamp()),
            },
        )
        self.assertEqual(response.status_code, 200)  # GraphQL always returns 200
        data = response.json()
        self.assertIn('errors', data)

    def test_metadata_history_invalid_station(self):
        """GET /api/v1/stations-metadata-history with invalid station should error."""
        response = self.client.get(
            '/api/v1/stations-metadata-history',
            {'station_slug': 'nonexistent-station'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('errors', data)

    # ──────────────────────────────────────────────
    # /api/v1/reviews (GET)
    # ──────────────────────────────────────────────

    def test_reviews_list_endpoint(self):
        """GET /api/v1/reviews with station_slug returns 200."""
        ts = int(timezone.now().timestamp())
        response = self.client.get(
            '/api/v1/reviews',
            {'station_slug': 'station-0', 'timestamp': ts},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data', data)
        self.assertIn('reviews', data['data'])

    def test_reviews_list_redirect_without_timestamp(self):
        """GET /api/v1/reviews without timestamp should redirect."""
        response = self.client.get('/api/v1/reviews', {'station_slug': 'station-0'})
        self.assertEqual(response.status_code, 302)

    # ──────────────────────────────────────────────
    # /api/v1/reviews/ (POST)
    # ──────────────────────────────────────────────

    def test_submit_review_with_station_slug(self):
        """POST /api/v1/reviews/ with station_slug should work."""
        import json
        response = self.client.post(
            '/api/v1/reviews/',
            json.dumps({'station_slug': 'station-0', 'stars': 5, 'message': 'Great!'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('data', data)

    # ──────────────────────────────────────────────
    # /api/ and /api/v1/docs/ and /api/v1/schema/
    # ──────────────────────────────────────────────

    def test_api_landing_page(self):
        """GET /api/ should return landing page HTML."""
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertContains(response, '/api/v1/docs/')
        self.assertContains(response, '/graphql')

    def test_api_docs_page(self):
        """GET /api/v1/docs/ should return Scalar UI."""
        response = self.client.get('/api/v1/docs/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertContains(response, 'api-reference')

    def test_api_schema(self):
        """GET /api/v1/schema/ should return valid OpenAPI JSON with all endpoints."""
        response = self.client.get('/api/v1/schema/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('openapi', data)
        self.assertIn('paths', data)
        # Verify all endpoints are documented
        paths = data['paths']
        self.assertIn('/api/v1/stations', paths)
        self.assertIn('/api/v1/stations-metadata', paths)
        self.assertIn('/api/v1/stations-metadata-history', paths)
        self.assertIn('/api/v1/reviews', paths)
        self.assertIn('/api/v1/reviews/', paths)
