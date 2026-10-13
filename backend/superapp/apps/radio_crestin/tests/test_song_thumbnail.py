"""Station logos sent in place of a song cover are not stored on songs."""

from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from ..models import Songs
from ..services.song_thumbnail import clean_song_thumbnail_url
from .helpers import make_station

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


class ScrapedSongThumbnailTests(TestCase):
    """The Celery scrape path stores what the pod path stores."""

    def test_station_logo_is_not_stored(self):
        from superapp.apps.radio_crestin_scraping.services import (
            StationService,
        )
        from superapp.apps.radio_crestin_scraping.utils.data_types import (
            SongData, StationNowPlayingData,
        )
        station = make_station('scraped-station')
        StationService.upsert_station_now_playing(
            station.id,
            StationNowPlayingData(
                current_song=SongData(
                    name='Voi canta', artist='Ekklesia',
                    thumbnail_url=STATION_LOGOS[0]),
                raw_data={}, error=[],
            ),
        )
        self.assertIsNone(Songs.objects.get(name='Voi canta').thumbnail_url)


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
