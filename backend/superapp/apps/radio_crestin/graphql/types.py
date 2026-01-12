from __future__ import annotations

import strawberry
import strawberry_django
from typing import Optional, List
from datetime import datetime
from enum import Enum

from django.conf import settings

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
            # Check if listener counts were pre-loaded
            if hasattr(self, '_listener_counts_cache'):
                return self._listener_counts_cache.get('radio_crestin', 0)
            
            # Fallback to individual query if not pre-loaded
            # Get count of unique active listeners from ListeningSessions
            # Active = had activity in the last 60 seconds
            return ListeningSessions.get_active_listeners_count(station=self, minutes=1)
        except Exception as e:
            if settings.DEBUG:
                raise e
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

        # Check if posts are already prefetched or cached to avoid N+1 queries
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
        elif hasattr(self, '_posts_cache'):
            # Use cached posts if available
            posts = self._posts_cache
            
            # Apply custom ordering if different from default
            if order_by and order_by.published and order_by.published != OrderDirection.desc:
                posts = sorted(posts, key=lambda p: p.published)
            elif order_by and order_by.published and order_by.published == OrderDirection.desc:
                posts = sorted(posts, key=lambda p: p.published, reverse=True)
            
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
            # Check if listener counts were pre-loaded
            if hasattr(self, '_listener_counts_cache'):
                total = self._listener_counts_cache.get('total', 0)
                return total if total > 0 else None
            
            # Fallback to individual calculation if not pre-loaded
            # Get radio-crestin specific listeners from real-time analytics
            radio_crestin_count = ListeningSessions.get_active_listeners_count(station=self, minutes=1)

            # Get external listeners from latest now playing data
            external_count = 0
            if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
                external_count = self.latest_station_now_playing.listeners or 0

            # Return the combined count
            # Note: This assumes external sources don't overlap with radio-crestin listeners
            total = radio_crestin_count + external_count
            return total if total > 0 else None

        except Exception as e:
            if settings.DEBUG:
                raise e
            # Fallback to just external count if there's an error
            if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
                return self.latest_station_now_playing.listeners
            return None

    @strawberry.field
    def reviews(self, info: strawberry.Info) -> List["ReviewType"]:
        """Get verified reviews for this station.

        Returns empty array by default. Only fetches actual reviews when
        include_reviews=true is passed in the request query parameters.
        """
        # Check if include_reviews is enabled in the request
        include_reviews = False
        if hasattr(info.context, 'request'):
            include_reviews = info.context.request.GET.get('include_reviews', '').lower() == 'true'

        if not include_reviews:
            return []

        from ..models import Reviews as ReviewsModel

        reviews = ReviewsModel.objects.filter(
            station_id=self.id,
            verified=True
        ).order_by('-created_at')

        return [
            ReviewType(
                id=r.id,
                station_id=None,
                stars=r.stars,
                message=r.message,
                user_identifier=None,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
                verified=None
            )
            for r in reviews
        ]

    @strawberry.field
    def reviews_stats(self) -> "ReviewsStatsType":
        """Get review statistics for this station."""
        from django.db.models import Avg, Count
        from ..models import Reviews as ReviewsModel

        stats = ReviewsModel.objects.filter(
            station_id=self.id,
            verified=True
        ).aggregate(
            count=Count('id'),
            avg_rating=Avg('stars')
        )

        return ReviewsStatsType(
            number_of_reviews=stats['count'] or 0,
            average_rating=round(stats['avg_rating'] or 0.0, 2)
        )


@strawberry_django.type(model=StationGroups, fields="__all__")
class StationGroupType:
    id: int = strawberry_django.field()
    station_to_station_groups: List[StationToStationGroupType] = strawberry_django.field(field_name="station_to_station_groups")


# Review types for GraphQL API
@strawberry.type
class ReviewsStatsType:
    """Statistics about reviews for a station"""
    number_of_reviews: int
    average_rating: float


@strawberry.type
class ReviewType:
    id: int
    station_id: int
    stars: int
    message: Optional[str]
    user_identifier: Optional[str]
    created_at: str
    updated_at: str
    verified: bool


@strawberry.input
class SubmitReviewInput:
    station_id: int
    stars: int = 5  # Default to 5 stars, validated in service to be 0-5
    message: Optional[str] = None
    user_identifier: Optional[str] = None


@strawberry.type
class SubmitReviewResponse:
    success: bool
    message: str
    review: Optional[ReviewType] = None
    created: bool = False


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

@strawberry.input
class CreateShareLinkInput:
    anonymous_id: str  # anonymous_id of the user
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

@strawberry.type
class ShareLinkData:
    share_id: str
    url: str
    share_message: str
    visit_count: int
    created_at: str
    is_active: bool
    share_section_title: Optional[str] = None
    share_section_message: Optional[str] = None
    share_station_message: Optional[str] = None

@strawberry.type
class CreateShareLinkResponse:
    success: bool
    message: str
    share_link: Optional[ShareLinkData] = None

@strawberry.type
class GetShareLinkResponse:
    success: bool
    message: str
    anonymous_id: Optional[str] = None
    share_link: Optional[ShareLinkData] = None
