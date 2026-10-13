import logging
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from superapp.apps.radio_crestin.services.history_timeline import (
    place_report,
)
from superapp.apps.radio_crestin.services.song_text import clean_song_text
from superapp.apps.radio_crestin.services.song_thumbnail import (
    check_song_thumbnail_later, screen_song_thumbnail_url,
)
from superapp.apps.radio_crestin.models import (
    Stations, StationsNowPlaying, StationsNowPlayingHistory,
    Songs, Artists,
)
from superapp.apps.radio_crestin.utils.cdn_proxy import (
    metadata_song_thumbnail_url,
)

logger = logging.getLogger(__name__)


def _parse_iso_timestamp(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))


class PodMetadataService:

    @staticmethod
    @transaction.atomic
    def report_metadata(input) -> dict:
        # The row lock serialises reports for one station (two pods report
        # it during a rolling update), which stamp_history_row needs to keep
        # the station's history strictly increasing. FOR NO KEY UPDATE
        # conflicts with itself but not with the key-share lock that
        # inserts referencing the station take (listening sessions, reviews,
        # history), so those never wait for this transaction.
        station = Stations.objects.select_for_update(no_key=True).get(
            slug=input.station_slug, disabled=False)
        song_title = clean_song_text(input.song_title)
        song_artist = clean_song_text(input.song_artist)
        if input.song_title and song_title is None:
            logger.warning("Ignoring non-title %r reported for %s",
                           input.song_title, input.station_slug)
        song_thumbnail_url = screen_song_thumbnail_url(input.thumbnail_url)

        # Upsert artist
        artist = None
        if song_artist:
            artist, _ = Artists.objects.get_or_create(
                name=song_artist,
                defaults={'dirty_metadata': input.dirty_metadata},
            )

        # Upsert song
        song = None
        if song_title:
            song_defaults = {
                'dirty_metadata': input.dirty_metadata,
            }
            if song_thumbnail_url:
                song_defaults['thumbnail_url'] = song_thumbnail_url
            song, _ = Songs.objects.update_or_create(
                name=song_title,
                artist=artist,
                defaults=song_defaults,
            )
            check_song_thumbnail_later(song.thumbnail_url)

        now = timezone.now()
        id3_ts = _parse_iso_timestamp(input.id3_timestamp)
        scraper_ts = _parse_iso_timestamp(input.scraper_timestamp)

        # Read previous state
        previous = StationsNowPlaying.objects.filter(
            station_id=station.id
        ).values('song_id', 'listeners', 'timestamp').first()

        new_song_id = song.id if song else None
        # A song change is dated by when it started in the stream.
        placed = place_report(station.id, previous, new_song_id,
                              input.listeners, scraper_ts or id3_ts or now, now)
        stamp = placed.history

        # Resolve thumbnail: prefer input, fallback to song's stored thumbnail
        thumbnail_url = song_thumbnail_url
        if not thumbnail_url and song and song.thumbnail_url:
            thumbnail_url = song.thumbnail_url

        now_playing, _ = StationsNowPlaying.objects.update_or_create(
            station_id=station.id,
            defaults={
                'timestamp': placed.song_started_at,
                'song': song,
                'listeners': input.listeners,
                'thumbnail_url': thumbnail_url,
                'raw_data': {'raw_title': input.raw_title or ''},
                'error': None,
            },
        )

        if stamp is not None:
            StationsNowPlayingHistory.objects.create(
                station_id=station.id,
                timestamp=stamp.timestamp,
                song_started_at=stamp.song_started_at,
                song=song,
                listeners=input.listeners,
                id3_timestamp=id3_ts,
                scraper_timestamp=scraper_ts,
                timestamp_source=input.timestamp_source,
            )

        # Update denormalized FK
        Stations.objects.filter(id=station.id).update(
            latest_station_now_playing=now_playing
        )

        # The song exactly as the API serves it (cleaned names, proxied
        # thumbnail), so pods can put it in the HLS playlist. `artist` is
        # the song's artist: the song was looked up by it.
        song_artist_row = artist if song else None
        return {
            'song_id': new_song_id,
            'song_title': song.name if song else None,
            'song_artist': song_artist_row.name if song_artist_row else None,
            'song_artist_id': song_artist_row.id if song_artist_row else None,
            'song_thumbnail_url': (
                metadata_song_thumbnail_url(song.thumbnail_url) if song else None
            ),
            'thumbnail_url': thumbnail_url,
            'history_timestamp': stamp.timestamp if stamp else None,
        }
