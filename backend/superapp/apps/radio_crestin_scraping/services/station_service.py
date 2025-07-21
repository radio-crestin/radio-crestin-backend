import logging
from typing import List, Optional, Dict, Any

from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone

from superapp.apps.radio_crestin.models import (
    Stations, StationsNowPlaying, StationsUptime,
    Songs, Artists, Posts
)
from ..utils.data_types import (
    StationNowPlayingData, StationUptimeData,
    StationRssFeedData, SongData
)

logger = logging.getLogger(__name__)


class StationService:
    """Service layer for station data operations"""

    @staticmethod
    def get_stations_with_metadata_fetchers():
        """Get all stations with their metadata fetch configurations"""
        return Stations.objects.select_related().prefetch_related(
            'station_metadata_fetches__station_metadata_fetch_category'
        ).filter(disabled=False)

    @staticmethod
    def get_stations_with_rss_feeds():
        """Get stations that have RSS feeds configured"""
        return Stations.objects.filter(
            disabled=False,
            rss_feed__isnull=False
        ).exclude(rss_feed='')

    @staticmethod
    @transaction.atomic
    def upsert_station_now_playing(station_id: int, data: StationNowPlayingData) -> bool:
        """Upsert station now playing data"""
        try:
            # Get or create song if we have song data
            song = None
            if data.current_song and (data.current_song.name or data.current_song.artist):
                song = StationService._upsert_song(data.current_song)

            # Upsert station now playing record
            now_playing, created = StationsNowPlaying.objects.update_or_create(
                station_id=station_id,
                defaults={
                    'timestamp': data.timestamp or timezone.now(),
                    'song': song,
                    'listeners': data.listeners,
                    'raw_data': data.raw_data,
                    'error': data.error,
                }
            )

            # Update station's latest_station_now_playing reference
            Stations.objects.filter(id=station_id).update(
                latest_station_now_playing=now_playing
            )

            logger.info(f"{'Created' if created else 'Updated'} now playing for station {station_id}")
            return True

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting station now playing for station {station_id}: {error}")
            return False

    @staticmethod
    @transaction.atomic
    def upsert_station_uptime(station_id: int, data: StationUptimeData) -> bool:
        """Upsert station uptime data"""
        try:
            uptime, created = StationsUptime.objects.update_or_create(
                station_id=station_id,
                defaults={
                    'timestamp': data.timestamp,
                    'is_up': data.is_up,
                    'latency_ms': data.latency_ms,
                    'raw_data': data.raw_data,
                }
            )

            # Update station's latest_station_uptime reference
            Stations.objects.filter(id=station_id).update(
                latest_station_uptime=uptime
            )

            logger.info(f"{'Created' if created else 'Updated'} uptime for station {station_id}")
            return True

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting station uptime for station {station_id}: {error}")
            return False

    @staticmethod
    @transaction.atomic
    def upsert_station_posts(station_id: int, rss_data: StationRssFeedData) -> bool:
        """Upsert station posts from RSS feed data"""
        if not rss_data.posts:
            return True

        try:
            posts_to_create = []
            posts_to_update = []

            for post_data in rss_data.posts:
                try:
                    # Check if post already exists
                    existing_post = Posts.objects.filter(
                        station_id=station_id,
                        link=post_data.link
                    ).first()

                    if existing_post:
                        # Update existing post
                        existing_post.title = post_data.title
                        existing_post.description = post_data.description
                        existing_post.published = post_data.published
                        posts_to_update.append(existing_post)
                    else:
                        # Create new post
                        posts_to_create.append(Posts(
                            station_id=station_id,
                            title=post_data.title,
                            link=post_data.link,
                            description=post_data.description,
                            published=post_data.published
                        ))

                except Exception as post_error:
                    if settings.DEBUG:
                        raise
                    logger.error(f"Error processing post {post_data.link}: {post_error}")
                    continue

            # Bulk operations
            if posts_to_create:
                Posts.objects.bulk_create(posts_to_create, ignore_conflicts=True)
                logger.info(f"Created {len(posts_to_create)} new posts for station {station_id}")

            if posts_to_update:
                Posts.objects.bulk_update(
                    posts_to_update,
                    ['title', 'description', 'published']
                )
                logger.info(f"Updated {len(posts_to_update)} posts for station {station_id}")

            return True

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting posts for station {station_id}: {error}")
            return False

    @staticmethod
    def _upsert_song(song_data: SongData) -> Optional[Songs]:
        """Upsert song and artist data"""
        try:
            # Get or create artist if we have artist name
            artist = None
            if song_data.artist:
                try:
                    artist, _ = Artists.objects.get_or_create(
                        name=song_data.artist,
                        defaults={'name': song_data.artist}
                    )
                except IntegrityError:
                    # Handle race condition - artist was created by another process
                    artist = Artists.objects.get(name=song_data.artist)

            # Get or create song
            song_defaults = {
                'name': song_data.name or '',
                'artist': artist,
            }

            if song_data.thumbnail_url:
                song_defaults['thumbnail_url'] = song_data.thumbnail_url

            # Use name and artist_id as unique constraint
            try:
                song, created = Songs.objects.update_or_create(
                    name=song_data.name or '',
                    artist=artist,
                    defaults=song_defaults
                )
            except IntegrityError:
                # Handle race condition - song was created by another process
                song = Songs.objects.get(name=song_data.name or '', artist=artist)

            return song

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting song {song_data.name}: {error}")
            return None

    @staticmethod
    def delete_old_data(days_to_keep: int = 30):
        """Delete old station data beyond specified days"""
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        try:
            # Delete old posts
            deleted_posts = Posts.objects.filter(
                created_at__lt=cutoff_date
            ).delete()

            logger.info(f"Deleted {deleted_posts[0]} old posts")

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error deleting old data: {error}")
            return False

        return True
