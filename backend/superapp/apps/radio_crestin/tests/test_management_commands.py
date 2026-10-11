"""Ops commands for the HLS streams and the now-playing data."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import (
    Artists, Songs, StationStreams, StationsNowPlaying,
    StationsNowPlayingHistory,
)
from .helpers import (
    DUMMY_CACHE, make_station, now_playing_of, report, song_name,
)

POD_HLS = 'https://live.radiocrestin.ro/hls/{}/index.m3u8'


def _hls(station, url=None, enabled=True):
    return StationStreams.objects.create(
        station=station, stream_url=url or POD_HLS.format(station.slug),
        type='HLS', enabled=enabled)


class CheckHlsStreamsCommandTests(TestCase):
    def _run(self):
        out = StringIO()
        call_command('check_hls_streams', stdout=out)
        return out.getvalue()

    def _failure(self):
        out = StringIO()
        with self.assertRaises(CommandError) as raised:
            call_command('check_hls_streams', stdout=out)
        self.assertEqual(raised.exception.returncode, 1)
        return out.getvalue()

    def test_consistent_stations_pass(self):
        _hls(make_station('transcoded'))
        tv = make_station('external-tv', transcode_enabled=False)
        _hls(tv, url='https://cdn.example.com/tv/master.m3u8')
        make_station('switched-off', disabled=True)
        self.assertIn('agree for every station', self._run())

    def test_transcoded_station_without_enabled_hls_stream_fails(self):
        make_station('no-hls-row')
        _hls(make_station('disabled-hls-row'), enabled=False)
        output = self._failure()
        self.assertIn('Transcoded without an enabled HLS stream: '
                      'disabled-hls-row', output)
        self.assertIn('Transcoded without an enabled HLS stream: no-hls-row',
                      output)

    def test_pod_hls_stream_without_transcoding_fails(self):
        station = make_station('not-transcoded', transcode_enabled=False)
        _hls(station)
        self.assertIn('HLS stream without transcoding: not-transcoded',
                      self._failure())


@override_settings(CACHES=DUMMY_CACHE)
class ClearGarbageNowPlayingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Stored before PodMetadataService rejected ffmpeg messages.
        garbage_station = make_station('alt-fm')
        song = Songs.objects.create(
            name='ChannelElement 3.1 missing',
            artist=Artists.objects.create(name='Unknown'))
        started = timezone.now() - timedelta(days=3)
        StationsNowPlayingHistory.objects.create(
            station=garbage_station, timestamp=started, song=song,
            listeners=4)
        StationsNowPlaying.objects.create(
            station=garbage_station, timestamp=started, song=song,
            listeners=4, raw_data={})
        make_station('fine-fm')

    def setUp(self):
        report('fine-fm', 'Real Song', listeners=2)

    def _run(self, *args):
        out = StringIO()
        call_command('clear_garbage_now_playing', *args, stdout=out)
        return out.getvalue()

    def _api_song(self, slug):
        t = int(timezone.now().timestamp()) + 1
        response = self.client.get('/api/v1/stations-metadata', {
            'timestamp': t, 'station_slugs': slug})
        return song_name(now_playing_of(response, slug))

    def test_dry_run_changes_nothing(self):
        history_rows = StationsNowPlayingHistory.objects.count()
        output = self._run()
        self.assertIn("alt-fm: 'ChannelElement 3.1 missing'", output)
        self.assertNotIn('fine-fm', output)
        self.assertEqual(StationsNowPlayingHistory.objects.count(), history_rows)
        self.assertEqual(self._api_song('alt-fm'), 'ChannelElement 3.1 missing')

    def test_apply_clears_only_garbage_songs(self):
        self._run('--apply')
        garbage = StationsNowPlaying.objects.get(station__slug='alt-fm')
        self.assertIsNone(garbage.song)
        self.assertIsNone(self._api_song('alt-fm'))
        self.assertEqual(self._api_song('fine-fm'), 'Real Song')
        # The old rows stay: answers for past instants do not change.
        rows = StationsNowPlayingHistory.objects.filter(
            station__slug='alt-fm').order_by('timestamp')
        self.assertEqual([r.song_id is None for r in rows], [False, True])
        self.assertEqual(rows.last().listeners, 4)
