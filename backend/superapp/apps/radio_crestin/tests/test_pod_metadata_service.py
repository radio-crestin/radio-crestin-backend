"""PodMetadataService: what a streaming pod's report stores and returns."""

import json
import os
import threading
from datetime import timedelta
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from ..management.commands.clear_garbage_now_playing import _clear_song
from ..models import (
    Artists, Songs, StationsNowPlaying, StationsNowPlayingHistory,
)
from ..services import history_timeline
from ..utils.cdn_proxy import CDN_BASE_URL
from .helpers import (
    DUMMY_CACHE, make_station, now_playing_of, report, whole_seconds_ago,
)

POD_KEY = 'test-pod-key'
REPORT_MUTATION = '''
mutation Report($input: ReportStationMetadataInput!) {
  report_station_metadata(input: $input) {
    ... on ReportStationMetadataResponse {
      success song_id song_title song_artist song_artist_id
      song_thumbnail_url thumbnail_url history_timestamp
    }
    ... on OperationInfo { messages { message } }
  }
}
'''


class PodReportCleaningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_station('garbage-station')

    def test_ffmpeg_message_is_not_stored_as_a_song(self):
        result = report('garbage-station', 'ChannelElement 3.1 missing')
        self.assertIsNone(result['song_id'])
        self.assertIsNone(result['song_artist'])
        self.assertFalse(
            Songs.objects.filter(name__icontains='ChannelElement').exists())

    def test_report_returns_what_was_stored(self):
        started = timezone.now() - timedelta(seconds=4)
        result = report('garbage-station', '  Real   Song ', started=started)
        song = Songs.objects.get(id=result['song_id'])
        self.assertEqual(result['song_title'], 'Real Song')
        self.assertEqual(result['song_artist'], 'Artist')
        self.assertEqual(result['song_artist_id'], song.artist_id)
        self.assertEqual(result['history_timestamp'], started)


@override_settings(CACHES=DUMMY_CACHE, CDN_SIGNING_SECRET='test-secret')
class ReportMutationTests(TestCase):
    """The song fields pods put in the playlist hint equal the API's."""

    @classmethod
    def setUpTestData(cls):
        make_station('mutation-station')

    def _report(self, **fields):
        variables = {'input': {'station_slug': 'mutation-station', **fields}}
        with patch.dict(os.environ, {'STREAMING_POD_API_KEY': POD_KEY}):
            response = self.client.post(
                '/graphql',
                json.dumps({'query': REPORT_MUTATION, 'variables': variables}),
                content_type='application/json',
                HTTP_X_STREAMING_API_KEY=POD_KEY,
            )
        self.assertEqual(response.status_code, 200)
        return response.json()['data']['report_station_metadata']

    def test_response_names_the_song_as_the_api_serves_it(self):
        started = whole_seconds_ago(30)
        result = self._report(
            song_title='Real Song', song_artist='Artist',
            thumbnail_url='https://img.example.com/song.jpg',
            scraper_timestamp=started.isoformat())

        self.assertTrue(result['success'])
        self.assertEqual(result['song_title'], 'Real Song')
        self.assertEqual(result['song_artist'], 'Artist')
        self.assertTrue(result['song_thumbnail_url'].startswith(CDN_BASE_URL))
        self.assertEqual(result['thumbnail_url'],
                         'https://img.example.com/song.jpg')
        self.assertIsNotNone(result['history_timestamp'])

        t = int(timezone.now().timestamp())
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': t, 'station_slugs': 'mutation-station'})
        song = now_playing_of(response, 'mutation-station')['song']
        self.assertEqual(result['song_id'], song['id'])
        self.assertEqual(result['song_title'], song['name'])
        self.assertEqual(result['song_artist'], song['artist']['name'])
        self.assertEqual(result['song_artist_id'], song['artist']['id'])
        self.assertEqual(result['song_thumbnail_url'], song['thumbnail_url'])


class PodReportConcurrencyTests(TransactionTestCase):
    """Two pods reporting one station at once (a rolling update)."""

    # Real commits are needed for the second report to wait on the first
    # one's row lock. Limiting the apps keeps the flush between tests to
    # these tables and skips its post_migrate signal, whose
    # django-guardian anonymous-user hook fails on this project's User.
    available_apps = ['superapp.apps.radio_crestin']

    def setUp(self):
        make_station('race-station')

    def test_concurrent_reports_get_distinct_increasing_timestamps(self):
        started = timezone.now() - timedelta(seconds=10)
        barrier = threading.Barrier(2)
        errors = []

        def pod(title, artist):
            try:
                barrier.wait(timeout=10)
                report('race-station', title, started=started, artist=artist)
            except Exception as error:  # surfaced by the assertion below
                errors.append(error)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=pod, args=('Song A', 'Artist A')),
            threading.Thread(target=pod, args=('Song B', 'Artist B')),
        ]
        with patch.object(history_timeline, '_newest_row',
                          side_effect=_newest_row_read_by_both()):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        self.assertEqual(errors, [])
        rows = list(StationsNowPlayingHistory.objects.filter(
            station__slug='race-station').order_by('id'))
        self.assertEqual(len(rows), 2)
        self.assertLess(rows[0].timestamp, rows[1].timestamp)
        self.assertLess(rows[0].song_started_at, rows[1].song_started_at)



class StationLockModeTests(TransactionTestCase):
    """Writers lock the station row FOR NO KEY UPDATE: they still wait for
    each other (PodReportConcurrencyTests), but an insert that only
    references the station (a listening session, a review, a history row)
    never waits for a writer's transaction, as it would behind FOR UPDATE.
    """

    available_apps = ['superapp.apps.radio_crestin']

    def setUp(self):
        self.station = make_station('lock-station')

    def test_pod_report_does_not_block_references(self):
        self._assert_reference_insert_not_blocked(
            lambda: report('lock-station', 'Song', listeners=1))

    def test_scraper_upsert_does_not_block_references(self):
        from superapp.apps.radio_crestin_scraping.services import (
            StationService,
        )
        from superapp.apps.radio_crestin_scraping.utils.data_types import (
            SongData, StationNowPlayingData,
        )
        self._assert_reference_insert_not_blocked(
            lambda: StationService.upsert_station_now_playing(
                self.station.id, StationNowPlayingData(
                    timestamp=timezone.now().isoformat(),
                    current_song=SongData(name='Song', artist='Artist'),
                    listeners=1, raw_data={}, error=[],
                )))

    def test_garbage_cleanup_does_not_block_references(self):
        song = Songs.objects.create(
            name='ChannelElement 3.1 missing',
            artist=Artists.objects.create(name='Unknown'))
        StationsNowPlaying.objects.create(
            station=self.station, timestamp=timezone.now() - timedelta(days=1),
            song=song, listeners=0, raw_data={})
        self._assert_reference_insert_not_blocked(
            lambda: _clear_song(self.station.id))

    def _assert_reference_insert_not_blocked(self, write):
        """Run `write` on another connection, hold its transaction open
        right after it locked the station (where it reads the newest
        history row), and insert a row referencing the station meanwhile."""
        locked, release = threading.Event(), threading.Event()
        real_newest_row = history_timeline._newest_row
        errors = []

        def paused(station_id):
            locked.set()
            release.wait(timeout=5)
            return real_newest_row(station_id)

        def writer():
            try:
                write()
            except Exception as error:  # surfaced by the assertion below
                errors.append(error)
            finally:
                connection.close()

        thread = threading.Thread(target=writer)
        with patch.object(history_timeline, '_newest_row', side_effect=paused):
            thread.start()
            try:
                self.assertTrue(locked.wait(timeout=5))
                self._insert_referencing_row()
            finally:
                release.set()
                thread.join(timeout=10)
        self.assertEqual(errors, [])

    def _insert_referencing_row(self):
        with connection.cursor() as cursor:
            cursor.execute("SET lock_timeout = '1s'")
        try:
            StationsNowPlayingHistory.objects.create(
                station=self.station,
                timestamp=timezone.now() - timedelta(hours=1))
        except OperationalError as error:
            self.fail(f'the insert waited for the station lock: {error}')
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SET lock_timeout = 0')

def _newest_row_read_by_both():
    """`history_timeline._newest_row` that holds the first reader's
    transaction open until a second report reads the newest row as well.

    Without the station row lock both reports then date themselves from the
    same newest row. With it, the second report cannot get here before the
    first one commits, so the first stops waiting after a second.
    """
    real_newest_row = history_timeline._newest_row
    readers = []
    readers_lock = threading.Lock()
    second_reader = threading.Event()

    def newest_row(station_id):
        row = real_newest_row(station_id)
        with readers_lock:
            readers.append(station_id)
            first = len(readers) == 1
        if first:
            second_reader.wait(timeout=1)
        else:
            second_reader.set()
        return row

    return newest_row
