import logging
from datetime import datetime, timezone as dt_tz
from typing import Optional

from django.db import transaction
from django.utils import timezone

from superapp.apps.radio_crestin.models import (
    Stations, StationsNowPlaying, StationsNowPlayingHistory,
    Songs, Artists,
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
        station = Stations.objects.get(slug=input.station_slug, disabled=False)

        # Upsert artist
        artist = None
        if input.song_artist:
            artist, _ = Artists.objects.get_or_create(
                name=input.song_artist,
                defaults={'dirty_metadata': input.dirty_metadata},
            )

        # Upsert song
        song = None
        if input.song_title:
            song_defaults = {
                'dirty_metadata': input.dirty_metadata,
            }
            if input.thumbnail_url:
                song_defaults['thumbnail_url'] = input.thumbnail_url
            song, _ = Songs.objects.update_or_create(
                name=input.song_title,
                artist=artist,
                defaults=song_defaults,
            )

        now = timezone.now()
        id3_ts = _parse_iso_timestamp(input.id3_timestamp)
        scraper_ts = _parse_iso_timestamp(input.scraper_timestamp)

        # Determine the primary timestamp based on the source
        primary_ts = scraper_ts or id3_ts or now

        # Read previous state
        previous = StationsNowPlaying.objects.filter(
            station_id=station.id
        ).values('song_id', 'listeners').first()

        # Resolve thumbnail: prefer input, fallback to song's stored thumbnail
        thumbnail_url = input.thumbnail_url
        if not thumbnail_url and song and song.thumbnail_url:
            thumbnail_url = song.thumbnail_url

        # Upsert now playing
        now_playing, created = StationsNowPlaying.objects.update_or_create(
            station_id=station.id,
            defaults={
                'timestamp': primary_ts,
                'song': song,
                'listeners': input.listeners,
                'thumbnail_url': thumbnail_url,
                'raw_data': {'raw_title': input.raw_title or ''},
                'error': None,
            },
        )

        # Write history on change
        new_song_id = song.id if song else None
        metadata_changed = (
            created
            or (previous['song_id'] if previous else None) != new_song_id
            or (previous['listeners'] if previous else None) != input.listeners
        )
        if metadata_changed:
            StationsNowPlayingHistory.objects.create(
                station_id=station.id,
                timestamp=primary_ts,
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

        return {
            'song_id': song.id if song else None,
            'thumbnail_url': thumbnail_url,
        }
