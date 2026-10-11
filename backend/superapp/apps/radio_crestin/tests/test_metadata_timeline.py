"""Timeline guarantees of the now-playing history behind /stations-metadata.

* An answer for `?timestamp=T` is only cached as immutable once no row dated
  at or before T can still arrive (METADATA_SETTLE_SECONDS).
* Every station's history timestamps are strictly increasing, so `<= T`
  lookups have one newest row; legacy ties resolve to the newest insert.
* Every row exposes the start of its song: listener-count rows are dated
  when the count changed, but never move the song timeline.
* `changes_from_timestamp` diffs look back far enough to include rows that
  were written after the client's previous diff but dated inside it.
"""

import time
from datetime import datetime, timedelta, timezone as dt_timezone
from email.utils import parsedate_to_datetime
from unittest.mock import patch

from django.core.cache import cache
from django.db import OperationalError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from ..graphql import queries, rest_endpoints
from ..graphql.queries import CHANGES_LOOKBACK_SECONDS
from ..graphql.rest_endpoints import METADATA_SETTLE_SECONDS
from ..models import (
    Artists, Songs, StationStreams, StationsNowPlaying,
    StationsNowPlayingHistory,
)
from ..services.listener_analytics_service import ListenerAnalyticsService
from ..services.history_timeline import (
    HISTORY_TIMESTAMP_STEP, METADATA_BACKDATE_LIMIT, stamp_history_row,
)
from .helpers import (
    DUMMY_CACHE, make_station, now_playing_of, report, reported_at,
    song_name, whole_seconds_ago,
)

LOCMEM_CACHE = {'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'metadata-timeline-tests',
}}
# validate_timestamp_not_future accepts T up to now + 2 s.
FUTURE_GUARD_SECONDS = 2


def _at(instant):
    """`instant` as the API renders it, for comparing with its JSON."""
    return instant.isoformat()


def _epoch(instant):
    return int(instant.timestamp())


class SettleBoundTests(SimpleTestCase):
    """The REST layer's windows must cover the writers' back-dating."""

    def test_settle_window_covers_backdating_and_clock_guard(self):
        bound = METADATA_BACKDATE_LIMIT.total_seconds() + FUTURE_GUARD_SECONDS
        self.assertGreater(METADATA_SETTLE_SECONDS, bound)
        self.assertGreater(CHANGES_LOOKBACK_SECONDS, bound)


@override_settings(CACHES=DUMMY_CACHE)
class StationsMetadataCachePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_station('policy-station')

    def _get(self, **params):
        return self.client.get('/api/v1/stations-metadata', params)

    def test_settled_window_is_immutable(self):
        ts = _epoch(timezone.now()) - METADATA_SETTLE_SECONDS - 10
        response = self._get(timestamp=ts)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'],
                         'public, max-age=2592000, immutable')

    def test_recent_window_is_short_lived(self):
        ts = _epoch(timezone.now()) - 10
        self.assertEqual(self._get(timestamp=ts)['Cache-Control'],
                         'public, max-age=60')

    def test_unsettled_copies_expire_before_offset_listeners_ask(self):
        # An unsettled copy is made before T + METADATA_SETTLE_SECONDS, so a
        # listener in the shortest offset mode (2 min) always gets the
        # settled answer, while Redis refreshes it within seconds.
        self.assertLessEqual(
            METADATA_SETTLE_SECONDS + rest_endpoints.METADATA_UNSETTLED_MAX_AGE,
            120)
        self.assertLess(rest_endpoints.UNSETTLED_METADATA_POLICY.ttl,
                        rest_endpoints.METADATA_UNSETTLED_MAX_AGE)

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_no_server_cache_outlives_the_unsettled_redis_ttl(self):
        # Django's page cache stores a page for its max-age (60 s here),
        # which would serve the unsettled answer long after Redis dropped it.
        cache.clear()
        self._get(timestamp=_epoch(timezone.now()) - 10)
        ttl = rest_endpoints.UNSETTLED_METADATA_POLICY.ttl
        lifetimes = [expiry - time.time()
                     for expiry in cache._expire_info.values()]
        self.assertTrue(lifetimes)
        self.assertLessEqual(max(lifetimes), ttl)

    def test_diff_requests_follow_the_same_policy(self):
        ts = _epoch(timezone.now()) - 10
        response = self._get(timestamp=ts, changes_from_timestamp=ts - 60)
        self.assertEqual(response['Cache-Control'], 'public, max-age=60')

    def test_timestamp_zero_means_now_and_is_short_lived(self):
        # The resolver reads timestamp=0 as "now", so it never settles.
        self.assertEqual(self._get(timestamp=0)['Cache-Control'],
                         'public, max-age=60')

    def test_response_says_when_it_was_generated(self):
        before = int(timezone.now().timestamp())
        response = self._get(timestamp=before - 10)
        generated = parsedate_to_datetime(response['Last-Modified'])
        self.assertGreaterEqual(generated.timestamp(), before)
        self.assertLessEqual(generated, timezone.now())


@override_settings(CACHES=DUMMY_CACHE)
class HistoryCachePolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_station('history-policy-station')

    def _get(self, **params):
        return self.client.get('/api/v1/stations-metadata-history', {
            'station_slug': 'history-policy-station', **params})

    def test_settled_range_is_immutable(self):
        to = _epoch(timezone.now()) - METADATA_SETTLE_SECONDS - 10
        response = self._get(from_timestamp=to - 600, to_timestamp=to)
        self.assertEqual(response['Cache-Control'],
                         'public, max-age=2592000, immutable')
        self.assertTrue(response.has_header('Last-Modified'))

    def test_recent_or_open_range_is_short_lived(self):
        to = _epoch(timezone.now()) - 5
        self.assertEqual(
            self._get(from_timestamp=to - 60, to_timestamp=to)['Cache-Control'],
            'public, max-age=60')
        self.assertEqual(self._get()['Cache-Control'], 'public, max-age=60')

    def test_range_starting_relative_to_now_is_short_lived(self):
        # Without from_timestamp the range starts an hour before now, so the
        # answer for this URL keeps moving even though `to` has settled.
        to = _epoch(timezone.now()) - METADATA_SETTLE_SECONDS - 10
        self.assertEqual(self._get(to_timestamp=to)['Cache-Control'],
                         'public, max-age=60')


@override_settings(CACHES=LOCMEM_CACHE)
class StationsMetadataLateRowTests(TestCase):
    """A row written after the first request for T must reach later readers."""

    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('late-row-station')
        artist = Artists.objects.create(name='Artist')
        cls.old = Songs.objects.create(name='Old Song', artist=artist)
        cls.new = Songs.objects.create(name='New Song', artist=artist)

    def setUp(self):
        cache.clear()

    def _name_at(self, t):
        response = self.client.get('/api/v1/stations-metadata', {'timestamp': t})
        return response, song_name(now_playing_of(response, 'late-row-station'))

    def test_settled_reader_sees_row_written_after_first_request(self):
        now = timezone.now()
        t = _epoch(now) - 20
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=now - timedelta(minutes=5),
            song=self.old)
        first, name = self._name_at(t)
        self.assertEqual(name, 'Old Song')
        self.assertEqual(first['Cache-Control'], 'public, max-age=60')
        # No cache is cleared here: the unsettled answer is kept under its
        # own key, so neither the endpoint's cache nor Django's page cache
        # (keyed on the URL alone) may hand it to the settled reader.
        # The new song started 2 s before T and was ingested after the
        # first request (the back-dated row the CDN used to freeze out).
        StationsNowPlayingHistory.objects.create(
            station=self.station,
            timestamp=datetime.fromtimestamp(t - 2, tz=dt_timezone.utc),
            song=self.new)
        later = now + timedelta(seconds=METADATA_SETTLE_SECONDS + 5)
        with patch.object(rest_endpoints.timezone, 'now', return_value=later):
            settled, name = self._name_at(t)
        self.assertEqual(settled['Cache-Control'],
                         'public, max-age=2592000, immutable')
        self.assertEqual(name, 'New Song')


@override_settings(CACHES=LOCMEM_CACHE)
class TransientErrorTests(TestCase):
    """A resolver failing on a settled range is cached by no layer: once
    the database recovers, the same URL gets the real, final answer."""

    @classmethod
    def setUpTestData(cls):
        make_station('flaky-station')

    def setUp(self):
        cache.clear()

    def test_error_on_a_settled_range_is_not_kept(self):
        to = _epoch(timezone.now()) - METADATA_SETTLE_SECONDS - 240
        params = {'station_slug': 'flaky-station',
                  'from_timestamp': to - 600, 'to_timestamp': to}
        lost = OperationalError('server closed the connection unexpectedly')
        with patch.object(queries.Stations.objects, 'filter',
                          side_effect=lost):
            failed = self.client.get('/api/v1/stations-metadata-history',
                                     params)
        self.assertIn('errors', failed.json())
        self.assertIn('no-store', failed['Cache-Control'])
        self.assertNotIn('public', failed['Cache-Control'])

        recovered = self.client.get('/api/v1/stations-metadata-history',
                                    params)
        self.assertNotIn('errors', recovered.json())
        self.assertEqual(recovered['Cache-Control'],
                         'public, max-age=2592000, immutable')


@override_settings(CACHES=LOCMEM_CACHE)
class CachePolicyKeyTests(SimpleTestCase):
    """A response computed while unsettled is never served as settled."""

    def setUp(self):
        cache.clear()

    def test_unsettled_entry_is_not_reused_once_settled(self):
        from superapp.apps.graphql.rest_api import (
            CachePolicy, HttpMethod, RestApiEndpoint,
        )
        from superapp.apps.graphql.rest_handler import GraphQLRestApiView

        policies = iter([
            CachePolicy('public, max-age=60', 5, 'unsettled'),
            CachePolicy('public, max-age=2592000, immutable', 10, 'settled'),
        ])

        class View(GraphQLRestApiView):
            endpoint_config = RestApiEndpoint(
                path='api/v1/things', graphql_query='query { things }',
                method=HttpMethod.GET,
                cache_policy=lambda request: next(policies))

        factory = RequestFactory()
        with patch.object(GraphQLRestApiView, '_execute_graphql',
                          side_effect=[{'data': {'v': 1}}, {'data': {'v': 2}}]
                          ) as execute:
            first = View()._handle_request(
                factory.get('/api/v1/things', {'timestamp': '100'}))
            second = View()._handle_request(
                factory.get('/api/v1/things', {'timestamp': '100'}))
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(first['Cache-Control'], 'public, max-age=60')
        self.assertEqual(second['Cache-Control'],
                         'public, max-age=2592000, immutable')


class HistoryStampTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('ts-station')
        cls.other = make_station('ts-other')

    def _row(self, stamp, station=None):
        return StationsNowPlayingHistory.objects.create(
            station=station or self.station, timestamp=stamp.timestamp,
            song_started_at=stamp.song_started_at)

    def test_tie_resolves_to_newest_insert(self):
        artist = Artists.objects.create(name='Artist')
        jingle = Songs.objects.create(name='Station ID', artist=artist)
        song = Songs.objects.create(name='Real Song', artist=artist)
        ts = timezone.now() - timedelta(minutes=10)
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=ts, song=jingle)
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=ts, song=song)
        t = _epoch(ts + timedelta(seconds=30))
        with override_settings(CACHES=DUMMY_CACHE):
            response = self.client.get('/api/v1/stations-metadata', {
                'timestamp': t, 'station_slugs': 'ts-station'})
        self.assertEqual(song_name(now_playing_of(response, 'ts-station')),
                         'Real Song')

    def test_timestamps_are_strictly_increasing(self):
        now = timezone.now()
        started = now - timedelta(seconds=5)
        first = self._row(stamp_history_row(self.station.id, started, now, True))
        second = stamp_history_row(self.station.id, started, now, True)
        self.assertEqual(second.timestamp,
                         first.timestamp + HISTORY_TIMESTAMP_STEP)

    def test_backdating_is_capped(self):
        now = timezone.now()
        stamp = stamp_history_row(
            self.station.id, now - timedelta(minutes=10), now, True)
        self.assertEqual(stamp.timestamp, now - METADATA_BACKDATE_LIMIT)
        self.assertEqual(stamp.song_started_at, now - METADATA_BACKDATE_LIMIT)

    def test_other_stations_do_not_affect_the_sequence(self):
        now = timezone.now()
        StationsNowPlayingHistory.objects.create(
            station=self.other, timestamp=now)
        started = now - timedelta(seconds=5)
        stamp = stamp_history_row(self.station.id, started, now, True)
        self.assertEqual(stamp.timestamp, started)

    def test_listener_row_repeats_the_song_start(self):
        now = timezone.now()
        started = now - timedelta(seconds=30)
        self._row(stamp_history_row(self.station.id, started, now, True))
        stamp = stamp_history_row(self.station.id, now, now, False)
        self.assertEqual(stamp.timestamp, now)
        self.assertEqual(stamp.song_started_at, started)

    def test_legacy_row_is_read_as_its_own_song_start(self):
        now = timezone.now()
        legacy = now - timedelta(minutes=3)
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=legacy)
        stamp = stamp_history_row(self.station.id, now, now, False)
        self.assertEqual(stamp.song_started_at, legacy)

    def test_a_song_never_starts_with_the_one_it_replaces(self):
        now = timezone.now()
        started = now - timedelta(seconds=20)
        first = self._row(stamp_history_row(self.station.id, started, now, True))
        second = stamp_history_row(self.station.id, started, now, True)
        self.assertGreater(second.song_started_at, first.song_started_at)

    def test_far_future_row_does_not_freeze_the_station(self):
        # Ordering after a row dated tomorrow would hide every new row
        # from `<= T` lookups until tomorrow.
        now = timezone.now()
        self._row(stamp_history_row(self.station.id, now, now, True))
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=now + timedelta(days=1))
        started = now + timedelta(seconds=1)
        stamp = stamp_history_row(self.station.id, started, now, True)
        self.assertEqual(stamp.timestamp, started)

    def test_row_within_the_future_limit_still_orders_new_rows(self):
        now = timezone.now()
        ahead = self._row(stamp_history_row(
            self.station.id, now + timedelta(seconds=30), now, True))
        stamp = stamp_history_row(self.station.id, now, now, False)
        self.assertEqual(stamp.timestamp,
                         ahead.timestamp + HISTORY_TIMESTAMP_STEP)

    def test_song_change_ordered_after_a_later_row_keeps_its_start(self):
        now = timezone.now()
        self._row(stamp_history_row(
            self.station.id, now - timedelta(seconds=40), now, True))
        listener = self._row(stamp_history_row(self.station.id, now, now, False))
        started = now - timedelta(seconds=10)
        stamp = stamp_history_row(self.station.id, started, now, True)
        self.assertEqual(stamp.timestamp,
                         listener.timestamp + HISTORY_TIMESTAMP_STEP)
        self.assertEqual(stamp.song_started_at, started)


@override_settings(CACHES=DUMMY_CACHE)
class PodReportTimelineTests(TestCase):
    """What the API shows after the reports a streaming pod sends."""

    @classmethod
    def setUpTestData(cls):
        make_station('pod-station')

    def _history(self):
        return list(StationsNowPlayingHistory.objects.filter(
            station__slug='pod-station').order_by('timestamp', 'id'))

    def _now_playing_at(self, t, **params):
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': t, 'station_slugs': 'pod-station', **params})
        return now_playing_of(response, 'pod-station')

    def _history_entries(self, start, end):
        response = self.client.get('/api/v1/stations-metadata-history', {
            'station_slug': 'pod-station',
            'from_timestamp': start, 'to_timestamp': end})
        return response.json()['data']['stations_metadata_history']['history']

    def test_song_change_is_dated_by_stream_start(self):
        started = timezone.now() - timedelta(seconds=8)
        report('pod-station', 'Song A', started=started)
        row = self._history()[-1]
        self.assertEqual(row.timestamp, started)
        self.assertEqual(row.song_started_at, started)

    def test_listener_only_change_is_dated_now_and_keeps_song_start(self):
        started = timezone.now() - timedelta(seconds=30)
        report('pod-station', 'Song A', started=started, listeners=5)
        before = timezone.now()
        report('pod-station', 'Song A', started=started, listeners=7)
        rows = self._history()
        self.assertEqual(len(rows), 2)
        self.assertGreaterEqual(rows[-1].timestamp, before)
        self.assertEqual(rows[-1].song_started_at, started)
        np = StationsNowPlaying.objects.get(station__slug='pod-station')
        self.assertEqual(np.timestamp, started)

    def test_scraped_change_with_stale_icy_start_does_not_tie(self):
        # Scraper mode used to send the ICY start of the *previous* song
        # with a new scraped song: two rows, one timestamp.
        started = timezone.now() - timedelta(seconds=20)
        report('pod-station', 'Jingle', started=started)
        report('pod-station', 'Real Song', started=started)
        rows = self._history()
        self.assertEqual(len({r.timestamp for r in rows}), len(rows))
        self.assertEqual(len({r.song_started_at for r in rows}), len(rows))
        self.assertEqual(rows[-1].song.name, 'Real Song')

    def test_now_playing_timestamp_stays_the_song_start(self):
        """Listener-count reports never move now_playing.timestamp."""
        start = whole_seconds_ago(600)
        with reported_at(start + timedelta(seconds=2)):
            report('pod-station', 'Song A', started=start, listeners=1)
        for n, offset in enumerate((10, 20, 30), start=2):
            with reported_at(start + timedelta(seconds=offset)):
                report('pod-station', 'Song A', started=start, listeners=n)
        t = _epoch(start) + 40
        self.assertEqual(self._now_playing_at(t)['timestamp'], _at(start))
        diff = self._now_playing_at(t, changes_from_timestamp=_epoch(start) + 25)
        self.assertEqual(diff['timestamp'], _at(start))
        self.assertEqual(diff['listeners'], 4)

    def test_song_announced_ahead_of_its_audio_shows_as_started_now(self):
        now = timezone.now()
        ahead = now + timedelta(seconds=30)
        with reported_at(now):
            report('pod-station', 'Song A', started=ahead)
        np = StationsNowPlaying.objects.get(station__slug='pod-station')
        self.assertEqual(np.timestamp, now)
        self.assertEqual(self._history()[-1].timestamp, ahead)

    def test_listener_report_between_song_change_and_its_report(self):
        """The old song's listener row lands after the new song began.

        The pod reports the old song's audience at B+3 s, then the new
        song (started at B) at B+8 s. The new song keeps its start B, and
        the history never lists the old song as starting inside [B-2, B+20].
        """
        old_start = whole_seconds_ago(900)
        new_start = old_start + timedelta(seconds=200)
        with reported_at(old_start + timedelta(seconds=5)):
            report('pod-station', 'Old Song', started=old_start, listeners=1)
        with reported_at(new_start + timedelta(seconds=3)):
            report('pod-station', 'Old Song', started=old_start, listeners=2)
        with reported_at(new_start + timedelta(seconds=8)):
            report('pod-station', 'New Song', started=new_start, listeners=2)

        b = _epoch(new_start)
        now_playing = self._now_playing_at(b + 5)
        self.assertEqual(song_name(now_playing), 'New Song')
        self.assertEqual(now_playing['timestamp'], _at(new_start))
        entries = self._history_entries(b - 2, b + 20)
        self.assertEqual([song_name(e) for e in entries], ['New Song'])
        self.assertEqual(entries[0]['timestamp'], _at(new_start))


@override_settings(CACHES=DUMMY_CACHE)
class HistoryRunDedupeTests(TestCase):
    """A song continuing into a range is not a run that starts inside it."""

    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('dedupe-station')
        artist = Artists.objects.create(name='Artist')
        cls.song = Songs.objects.create(name='Long Song', artist=artist)
        cls.next = Songs.objects.create(name='Next Song', artist=artist)

    def _entries(self, start, end):
        response = self.client.get('/api/v1/stations-metadata-history', {
            'station_slug': 'dedupe-station',
            'from_timestamp': _epoch(start), 'to_timestamp': _epoch(end)})
        return response.json()['data']['stations_metadata_history']['history']

    def _row(self, timestamp, song, started=None):
        StationsNowPlayingHistory.objects.create(
            station=self.station, timestamp=timestamp, song=song,
            song_started_at=started)

    def test_continuing_song_is_not_listed(self):
        start = whole_seconds_ago(1200)
        self._row(start, self.song)
        self._row(start + timedelta(seconds=300), self.song, started=start)
        self._row(start + timedelta(seconds=400), self.next)
        entries = self._entries(start + timedelta(seconds=200),
                                start + timedelta(seconds=500))
        self.assertEqual([e['song']['name'] for e in entries], ['Next Song'])

    def test_range_without_an_earlier_row_lists_its_first_song(self):
        start = whole_seconds_ago(1200)
        self._row(start + timedelta(seconds=300), self.song, started=start)
        entries = self._entries(start + timedelta(seconds=200),
                                start + timedelta(seconds=500))
        self.assertEqual([e['song']['name'] for e in entries], ['Long Song'])
        self.assertEqual(entries[0]['timestamp'], _at(start))


@override_settings(CACHES=DUMMY_CACHE)
class ChangesFromLookbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('diff-station')
        artist = Artists.objects.create(name='Artist')
        cls.song = Songs.objects.create(name='Back-dated Song', artist=artist)

    def test_row_dated_before_changes_from_is_still_reported(self):
        now = _epoch(timezone.now())
        t, c = now - 5, now - 15
        # Written after the client's previous diff (C-10, C] but dated in it.
        StationsNowPlayingHistory.objects.create(
            station=self.station,
            timestamp=datetime.fromtimestamp(c - 3, tz=dt_timezone.utc),
            song=self.song)
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': t, 'changes_from_timestamp': c})
        self.assertEqual(song_name(now_playing_of(response, 'diff-station')),
                         'Back-dated Song')


class ScrapedHistoryTests(TestCase):
    """Rows of Celery-scraped stations follow the same timeline."""

    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('scraped-station', transcode_enabled=False)

    def _scrape(self, title, listeners):
        from superapp.apps.radio_crestin_scraping.services import StationService
        from superapp.apps.radio_crestin_scraping.utils.data_types import (
            SongData, StationNowPlayingData,
        )
        StationService.upsert_station_now_playing(
            self.station.id, StationNowPlayingData(
                timestamp=timezone.now().isoformat(),
                current_song=SongData(name=title, artist='Artist'),
                listeners=listeners, raw_data={}, error=[],
            ))

    def _history(self):
        return list(StationsNowPlayingHistory.objects.filter(
            station=self.station).order_by('timestamp', 'id'))

    def _now_playing(self):
        return StationsNowPlaying.objects.get(station=self.station)

    def test_listener_only_scrape_keeps_the_song_start(self):
        self._scrape('Song A', listeners=3)
        self._scrape('Song A', listeners=4)
        first, second = self._history()
        self.assertEqual(first.song_started_at, first.timestamp)
        self.assertGreater(second.timestamp, first.timestamp)
        self.assertEqual(second.song_started_at, first.timestamp)

    def test_now_playing_timestamp_is_the_song_start(self):
        """A scrape's own timestamp never moves now_playing.timestamp."""
        self._scrape('Song A', listeners=3)
        started = self._now_playing().timestamp
        self._scrape('Song A', listeners=3)
        self._scrape('Song A', listeners=4)
        self.assertEqual(self._now_playing().timestamp, started)
        self._scrape('Song B', listeners=4)
        self.assertEqual(self._now_playing().timestamp,
                         self._history()[-1].song_started_at)
        self.assertGreater(self._now_playing().timestamp, started)

    def test_ffmpeg_message_is_not_stored_as_a_song(self):
        self._scrape('[aac @ 0x55d5c8a3e2c0] ChannelElement 3.1 missing', 1)
        self.assertFalse(
            Songs.objects.filter(name__icontains='ChannelElement').exists())
        self._scrape('  Real   Song ', 1)
        self.assertEqual(self._now_playing().song.name, 'Real Song')


@override_settings(CACHES=DUMMY_CACHE)
class NearNowListenersTests(TestCase):
    """Counts taken now only go into answers that can still change: a
    settled answer is cached as immutable."""

    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('listeners-station')
        StationsNowPlayingHistory.objects.create(
            station=cls.station, listeners=3,
            timestamp=timezone.now() - timedelta(minutes=10))

    def _get(self, seconds_ago):
        live_counts = {self.station.id: 7}
        with patch.object(ListenerAnalyticsService, 'get_batch_listener_counts',
                          return_value=live_counts):
            return self.client.get('/api/v1/stations-metadata', {
                'timestamp': _epoch(timezone.now()) - seconds_ago,
                'station_slugs': 'listeners-station'})

    def _listeners(self, response):
        return now_playing_of(response, 'listeners-station')['listeners']

    def test_settled_answer_has_no_live_counts(self):
        response = self._get(METADATA_SETTLE_SECONDS + 10)
        self.assertEqual(response['Cache-Control'],
                         'public, max-age=2592000, immutable')
        self.assertEqual(self._listeners(response), 3)

    def test_unsettled_answer_adds_live_counts(self):
        response = self._get(10)
        self.assertEqual(response['Cache-Control'], 'public, max-age=60')
        self.assertEqual(self._listeners(response), 3 + 7)


@override_settings(CACHES=DUMMY_CACHE)
class EnabledStationStreamsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        station = make_station('streams-station')
        StationStreams.objects.create(
            station=station, stream_url='https://a/hls.m3u8', type='HLS',
            station_stream_order=0)
        StationStreams.objects.create(
            station=station, stream_url='https://a/live.mp3',
            type='direct_stream', station_stream_order=1, enabled=False)

    def test_disabled_streams_are_not_published(self):
        ts = _epoch(timezone.now())
        response = self.client.get('/api/v1/stations', {
            'timestamp': ts, 'station_slugs': 'streams-station'})
        streams = response.json()['data']['stations'][0]['station_streams']
        self.assertEqual([s['stream_url'] for s in streams],
                         ['https://a/hls.m3u8'])
