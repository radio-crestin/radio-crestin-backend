from django.test import TestCase
from django.utils import timezone

from ..admin.stations import StationsAdmin
from ..models import Stations, StationsNowPlaying
from superapp.apps.admin_portal.sites import superapp_admin_site
from .helpers import make_station


class NowPlayingDisplayTests(TestCase):
    def test_timestamp_is_labelled_as_the_song_start(self):
        station = make_station('admin-station')
        station.latest_station_now_playing = StationsNowPlaying.objects.create(
            station=station, timestamp=timezone.now(), listeners=0,
            raw_data={})
        html = StationsAdmin(Stations, superapp_admin_site).now_playing_display(station)
        self.assertIn('Started:', html)
        self.assertNotIn('Updated:', html)
