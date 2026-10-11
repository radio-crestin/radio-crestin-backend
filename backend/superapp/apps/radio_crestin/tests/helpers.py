"""Builders shared by the now-playing timeline tests."""

from contextlib import contextmanager
from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.utils import timezone

from ..models import Stations
from ..services import pod_metadata_service
from ..services.pod_metadata_service import PodMetadataService

DUMMY_CACHE = {'default': {
    'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
}}


def make_station(slug, **extra):
    return Stations.objects.create(
        slug=slug, title=slug, order=0, station_order=0.0,
        website='https://example.com', stream_url=f'https://example.com/{slug}',
        **extra,
    )


def report(slug, title, started=None, listeners=None, artist='Artist',
           thumbnail_url=None):
    """What a streaming pod sends: `started` is the song's stream start."""
    return PodMetadataService.report_metadata(SimpleNamespace(
        station_slug=slug, song_title=title, song_artist=artist,
        thumbnail_url=thumbnail_url, listeners=listeners,
        raw_title=f'{artist} - {title}', timestamp_source='scraper',
        id3_timestamp=None,
        scraper_timestamp=started.isoformat() if started else None,
        dirty_metadata=True,
    ))


@contextmanager
def reported_at(instant):
    """Run a report as if the server clock read `instant`."""
    with patch.object(pod_metadata_service.timezone, 'now',
                      return_value=instant):
        yield


def whole_seconds_ago(seconds):
    """An aware UTC instant on a whole second, `seconds` before now."""
    return datetime.fromtimestamp(
        int(timezone.now().timestamp()) - seconds, tz=dt_timezone.utc)


def now_playing_of(response, slug):
    """The `now_playing` of one station in a /stations-metadata response."""
    for station in response.json()['data']['stations_metadata']:
        if station['slug'] == slug:
            return station['now_playing'] or {}
    return None


def song_name(now_playing):
    return ((now_playing or {}).get('song') or {}).get('name')
