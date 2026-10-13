"""Station logos sent in place of a song cover are not stored on songs."""

from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from unittest.mock import patch

from django.apps import apps
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from ..models import Songs, SongThumbnailChecks, StationsNowPlaying
from ..services.song_thumbnail import (
    PLACEHOLDER_IMAGES_DIR, clean_song_thumbnail_url, is_placeholder_image,
)
from ..tasks.check_song_thumbnail import _is_public_http_url
from .helpers import make_station, report

# The module, not the task: the tasks package exports the task under the
# module's name.
check_task = import_module(
    'superapp.apps.radio_crestin.tasks.check_song_thumbnail')

INSTRUMENTAL_LOGO = (
    PLACEHOLDER_IMAGES_DIR / 'aripisprecer_instrumental.jpg').read_bytes()
# A URL per song, so only its file shows it is the logo.
VA_INST = ('https://pictures.aripisprecer.ro/instrumental/'
           'az_B313187_VA%20INST%2019_Tabara%20477.jpg')
COVER = 'https://pictures.aripisprecer.ro/general/az_42798_Diana.png'
COVER_2 = 'https://is4-ssl.mzstatic.com/image/thumb/Music2/v4/source/100x100bb.jpg'

STATION_LOGOS = (
    'https://pictures.aripisprecer.ro/general/na.png',
    'https://pictures.aripisprecer.ro/instrumental/na.png',
    'https://images.radio.co/station_logos/sb94ce6fe2.20180221082855.png',
    'https://asculta.radiofiladelfia.ro:8500/meta/albumart/no_cover_image.jpg',
    'no_cover_image.jpg',
)
COVERS = (
    # Ends in "na.png" without being Aripi Spre Cer's logo.
    'https://pictures.aripisprecer.ro/general/az_42798_Diana.png',
    'https://images.radio.co/album_art/sb94ce6fe2/playlist.804313.100.png',
    'https://is4-ssl.mzstatic.com/image/thumb/Music2/v4/source/100x100bb.jpg',
    'https://cdn.example.com/na.png',
)


class CleanSongThumbnailUrlTests(SimpleTestCase):
    def test_station_logos_are_rejected(self):
        for url in STATION_LOGOS:
            with self.subTest(url=url):
                self.assertIsNone(clean_song_thumbnail_url(url))

    def test_covers_survive(self):
        for url in COVERS:
            with self.subTest(url=url):
                self.assertEqual(clean_song_thumbnail_url(f' {url} '), url)

    def test_empty_values_are_none(self):
        for url in (None, '', '   '):
            with self.subTest(url=url):
                self.assertIsNone(clean_song_thumbnail_url(url))


class PlaceholderImageTests(SimpleTestCase):
    def test_every_placeholder_file_is_recognised(self):
        files = [p for p in PLACEHOLDER_IMAGES_DIR.iterdir() if p.suffix != '.md']
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            with self.subTest(file=path.name):
                self.assertTrue(is_placeholder_image(path.read_bytes()))

    def test_only_identical_bytes_match(self):
        """A re-saved copy is a different file: the rule is exact."""
        self.assertFalse(is_placeholder_image(INSTRUMENTAL_LOGO + b'\0'))
        self.assertFalse(is_placeholder_image(b'a cover'))


class PublicUrlTests(SimpleTestCase):
    def test_internal_and_non_http_urls_are_not_downloaded(self):
        for url in ('http://127.0.0.1/a.png', 'http://10.0.0.5/a.png',
                    'http://169.254.169.254/latest', 'http://[::1]/a.png',
                    'ftp://8.8.8.8/a.png', 'no_cover_image.jpg',
                    'http://8.8.8.8:notaport/a.png'):
            with self.subTest(url=url):
                self.assertFalse(_is_public_http_url(url))

    def test_public_address_is_downloaded(self):
        self.assertTrue(_is_public_http_url('https://8.8.8.8/a.png'))


class CheckSongThumbnailTaskTests(TestCase):
    """The file behind a URL decides, whatever the URL looks like."""

    @classmethod
    def setUpTestData(cls):
        cls.logo_songs = [
            Songs.objects.create(name=f'VA INST {i}', thumbnail_url=VA_INST)
            for i in (1, 2)]
        cls.cover_song = Songs.objects.create(name='Cover', thumbnail_url=COVER)
        StationsNowPlaying.objects.create(
            station=make_station('aripi-spre-cer-instrumental'),
            timestamp=timezone.now(), thumbnail_url=VA_INST, raw_data={})

    def _check(self, url, content):
        with patch.object(check_task, '_download',
                          return_value=content) as download:
            check_task.check_song_thumbnail(url)
        return download

    def test_placeholder_file_is_cleared_from_every_song(self):
        self._check(VA_INST, INSTRUMENTAL_LOGO)
        for song in self.logo_songs:
            song.refresh_from_db()
            self.assertIsNone(song.thumbnail_url)
        self.assertIsNone(StationsNowPlaying.objects.get().thumbnail_url)
        self.assertTrue(SongThumbnailChecks.objects.get(url=VA_INST).is_placeholder)
        self.cover_song.refresh_from_db()
        self.assertEqual(self.cover_song.thumbnail_url, COVER)

    def test_cover_is_kept(self):
        self._check(COVER, b'a cover')
        self.cover_song.refresh_from_db()
        self.assertEqual(self.cover_song.thumbnail_url, COVER)
        self.assertFalse(SongThumbnailChecks.objects.get(url=COVER).is_placeholder)

    def test_each_url_is_downloaded_once(self):
        self._check(COVER, b'a cover')
        self._check(COVER, b'a cover').assert_not_called()

    def test_failed_download_is_checked_again_later(self):
        self._check(COVER, None)
        self.assertFalse(SongThumbnailChecks.objects.exists())


class ReportedThumbnailCheckTests(TestCase):
    """Both report paths skip URLs found to be logos and have new ones
    checked once the report is committed."""

    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('scraped-station')
        make_station('pod-station')
        SongThumbnailChecks.objects.create(
            url=VA_INST, sha256='0' * 64, is_placeholder=True)

    def _scrape(self, name, thumbnail_url):
        from superapp.apps.radio_crestin_scraping.services import (
            StationService,
        )
        from superapp.apps.radio_crestin_scraping.utils.data_types import (
            SongData, StationNowPlayingData,
        )
        StationService.upsert_station_now_playing(
            self.station.id,
            StationNowPlayingData(
                current_song=SongData(
                    name=name, artist='Ekklesia', thumbnail_url=thumbnail_url),
                raw_data={}, error=[],
            ),
        )
        return Songs.objects.get(name=name)

    def test_scraped_station_logo_url_is_not_stored(self):
        self.assertIsNone(self._scrape('Voi canta', STATION_LOGOS[0]).thumbnail_url)

    def test_logo_found_by_its_file_is_not_stored_again(self):
        self.assertIsNone(self._scrape('Jertfa Ta', VA_INST).thumbnail_url)
        result = report('pod-station', 'Acasa', thumbnail_url=VA_INST)
        self.assertIsNone(Songs.objects.get(id=result['song_id']).thumbnail_url)

    def test_new_thumbnail_is_checked_after_the_report_commits(self):
        with patch.object(check_task.check_song_thumbnail, 'delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                report('pod-station', 'Cover Song', thumbnail_url=COVER)
                delay.assert_not_called()
            with self.captureOnCommitCallbacks(execute=True):
                self._scrape('Scraped Cover', COVER_2)
        self.assertEqual([c.args for c in delay.call_args_list],
                         [(COVER,), (COVER_2,)])

    def test_checked_thumbnail_is_not_checked_again(self):
        SongThumbnailChecks.objects.create(
            url=COVER, sha256='1' * 64, is_placeholder=False)
        with patch.object(check_task.check_song_thumbnail, 'delay') as delay:
            with self.captureOnCommitCallbacks(execute=True):
                report('pod-station', 'Cover Song', thumbnail_url=COVER)
        delay.assert_not_called()


class ClearStationLogoMigrationTests(TestCase):
    """Migration 0053 clears the logos stored before reports were
    filtered, and keeps the covers."""

    def test_clears_only_station_logos(self):
        migration = import_module(
            'superapp.apps.radio_crestin.migrations.'
            '0053_clear_station_logo_song_thumbnails')
        logos = [Songs.objects.create(name=f'logo {i}', thumbnail_url=url)
                 for i, url in enumerate(STATION_LOGOS)]
        covers = [Songs.objects.create(name=f'cover {i}', thumbnail_url=url)
                  for i, url in enumerate(COVERS)]

        with redirect_stdout(StringIO()):
            migration.clear_station_logo_thumbnails(apps, None)

        for song in logos:
            song.refresh_from_db()
            self.assertIsNone(song.thumbnail_url, song.name)
        for song, url in zip(covers, COVERS):
            song.refresh_from_db()
            self.assertEqual(song.thumbnail_url, url)
