from __future__ import annotations

import strawberry
import strawberry_django
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .scalars import timestamptz

class OrderDirection(Enum):
    asc = "asc"
    desc = "desc"

OrderDirectionEnum = strawberry.enum(OrderDirection)

@strawberry.input
class PostOrderBy:
    published: Optional[OrderDirectionEnum] = None

@strawberry.input
class ListeningEventInput:
    anonymous_session_id: str
    station_slug: str
    ip_address: str
    user_agent: str
    timestamp: str  # ISO format string
    event_type: str  # 'playlist_request' or 'segment_request'
    bytes_transferred: int
    request_duration: float
    status_code: int
    request_count: Optional[int] = None

from ..models import (
    Artists,
    Songs,
    Stations,
    Posts,
    StationStreams,
    StationsUptime,
    StationsNowPlaying,
    StationGroups,
    StationToStationGroup,
    ListeningSessions,
)


@strawberry_django.type(model=Artists, fields="__all__")
class ArtistType:
    id: int = strawberry_django.field()


@strawberry_django.type(model=Songs, fields="__all__")
class SongType:
    id: int = strawberry_django.field()
    artist_id: Optional[int] = strawberry_django.field()
    artist: Optional[ArtistType] = strawberry_django.field()


@strawberry_django.type(model=StationStreams, fields="__all__")
class StationStreamType:
    id: int = strawberry_django.field()
    station_id: int = strawberry_django.field()


@strawberry_django.type(model=Posts, fields="__all__")
class PostType:
    id: int = strawberry_django.field()
    station_id: int = strawberry_django.field()


@strawberry_django.type(model=StationsUptime, fields="__all__")
class StationUptimeType:
    id: int = strawberry_django.field()
    station_id: int = strawberry_django.field()
    # Add snake_case aliases for backward compatibility
    is_up: bool = strawberry_django.field()
    latency_ms: Optional[int] = strawberry_django.field()


@strawberry_django.type(model=StationsNowPlaying, fields="__all__")
class StationNowPlayingType:
    id: int = strawberry_django.field()
    station_id: int = strawberry_django.field()
    song_id: Optional[int] = strawberry_django.field()
    listeners: Optional[int] = strawberry_django.field()
    song: Optional[SongType] = strawberry_django.field()


@strawberry_django.type(model=StationToStationGroup, fields="__all__")
class StationToStationGroupType:
    id: int = strawberry_django.field()
    station_id: int = strawberry_django.field()
    group_id: int = strawberry_django.field()


@strawberry_django.type(model=Stations, fields="__all__")
class StationType:
    id: int = strawberry_django.field()
    latest_station_uptime_id: Optional[int] = strawberry_django.field()
    latest_station_now_playing_id: Optional[int] = strawberry_django.field()
    # Related fields optimized for the Hasura query
    station_streams: List[StationStreamType] = strawberry_django.field(field_name="station_streams")
    uptime: Optional[StationUptimeType] = strawberry_django.field(field_name="latest_station_uptime")
    now_playing: Optional[StationNowPlayingType] = strawberry_django.field(field_name="latest_station_now_playing")

    # Add snake_case aliases for backward compatibility
    thumbnail_url: Optional[str] = strawberry_django.field()
    description_action_title: Optional[str] = strawberry_django.field()
    description_link: Optional[str] = strawberry_django.field()
    feature_latest_post: bool = strawberry_django.field()
    facebook_page_id: Optional[str] = strawberry_django.field()

    # Hasura-compatible computed fields
    @strawberry.field
    def hls_stream_url(self) -> Optional[str]:
        """Generate HLS stream URL for the station"""
        if hasattr(self, 'generate_hls_stream') and self.generate_hls_stream:
            # Generate HLS URL based on station slug or ID
            return f"https://hls-staging.radio-crestin.com/{self.slug}/index.m3u8"
        return None

    @strawberry.field
    def proxy_stream_url(self) -> Optional[str]:
        """Generate proxy stream URL for the station"""
        return f"https://proxy.radio-crestin.com/{self.stream_url}"

    @strawberry.field
    def radio_crestin_listeners(self) -> Optional[int]:
        """Get listener count specific to radio-crestin platform from real-time analytics"""
        try:
            # Get count of unique active listeners from ListeningSessions
            # Active = had activity in the last 60 seconds
            return ListeningSessions.get_active_listeners_count(station=self, minutes=1)
        except Exception:
            # Fallback to 0 if there's an error accessing the sessions
            return 0

    # Custom posts resolver to handle limit and order_by
    @strawberry.field
    def posts(
        self,
        limit: Optional[int] = None,
        order_by: Optional[PostOrderBy] = None
    ) -> List[PostType]:
        """Get posts with limit and ordering support, optimized to use prefetched data when available"""
        from ..models import Posts

        # Check if posts are already prefetched to avoid N+1 queries
        if hasattr(self, '_prefetched_objects_cache') and 'posts' in self._prefetched_objects_cache:
            # Use prefetched data - it's already ordered by -published from the main query
            posts = list(self._prefetched_objects_cache['posts'])

            # Apply custom ordering if different from default
            if order_by and order_by.published and order_by.published != OrderDirection.desc:
                posts.sort(key=lambda p: p.published)

            # Apply limit
            if limit:
                posts = posts[:limit]

            return posts
        else:
            # Fallback to individual query if not prefetched
            queryset = Posts.objects.filter(station=self)

            # Apply ordering
            if order_by and order_by.published:
                if order_by.published == OrderDirection.desc:
                    queryset = queryset.order_by('-published')
                else:
                    queryset = queryset.order_by('published')
            else:
                # Default ordering
                queryset = queryset.order_by('-published')

            # Apply limit
            if limit:
                queryset = queryset[:limit]

            return list(queryset)

    # Additional computed fields for backward compatibility
    @strawberry.field
    def total_listeners(self) -> Optional[int]:
        """Get total listener count from both now playing data and radio-crestin analytics"""
        try:
            # Get radio-crestin specific listeners from real-time analytics
            radio_crestin_count = self.radio_crestin_listeners() or 0

            # Get external listeners from latest now playing data
            external_count = 0
            if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
                external_count = self.latest_station_now_playing.listeners or 0

            # Return the combined count
            # Note: This assumes external sources don't overlap with radio-crestin listeners
            total = radio_crestin_count + external_count
            return total if total > 0 else None

        except Exception:
            # Fallback to just external count if there's an error
            if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
                return self.latest_station_now_playing.listeners
            return None

    @strawberry.field
    def reviews(self) -> List[ReviewType]:
        """Placeholder for reviews - not implemented in current schema"""
        return []


@strawberry_django.type(model=StationGroups, fields="__all__")
class StationGroupType:
    id: int = strawberry_django.field()
    station_to_station_groups: List[StationToStationGroupType] = strawberry_django.field(field_name="station_to_station_groups")


# Placeholder for reviews type since it's not in the current Django schema
@strawberry.type
class ReviewType:
    id: int
    stars: int
    message: str


@strawberry.type
class GetStationsResponse:
    """
    Response type that exactly matches the Hasura GetStations query structure.
    This ensures complete backward compatibility for existing clients.
    """
    stations: List[StationType]
    station_groups: List[StationGroupType]

@strawberry.type
class SubmitListeningEventsResponse:
    success: bool
    message: str
    processed_count: int

@strawberry.type
class TriggerMetadataFetchResponse:
    success: bool
    message: str
