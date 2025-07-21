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
)


@strawberry_django.type(model=Artists, fields="__all__")
class ArtistType:
    pass


@strawberry_django.type(model=Songs, fields="__all__")
class SongType:
    artist: Optional[ArtistType] = strawberry_django.field()


@strawberry_django.type(model=StationStreams, fields="__all__")
class StationStreamType:
    pass


@strawberry_django.type(model=Posts, fields="__all__")
class PostType:
    pass


@strawberry_django.type(model=StationsUptime, fields="__all__")
class StationUptimeType:
    # Add snake_case aliases for backward compatibility  
    is_up: bool = strawberry_django.field()
    latency_ms: Optional[int] = strawberry_django.field()


@strawberry_django.type(model=StationsNowPlaying, fields="__all__")
class StationNowPlayingType:
    song: Optional[SongType] = strawberry_django.field()


@strawberry_django.type(model=StationToStationGroup, fields="__all__")
class StationToStationGroupType:
    # Add snake_case aliases for backward compatibility
    station_id: Optional[int] = strawberry_django.field(field_name="station_id")


@strawberry_django.type(model=Stations, fields="__all__")
class StationType:
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
            return f"https://hls.radio-crestin.com/{self.slug}.m3u8"
        return None
    
    @strawberry.field
    def proxy_stream_url(self) -> Optional[str]:
        """Generate proxy stream URL for the station"""
        return f"https://proxy.radio-crestin.com/{self.slug}"
    
    @strawberry.field
    def radio_crestin_listeners(self) -> Optional[int]:
        """Get listener count specific to radio-crestin platform"""
        if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
            # Assume this is radio-crestin specific count
            return self.latest_station_now_playing.listeners
        return None
    
    # Custom posts resolver to handle limit and order_by
    @strawberry.field
    def posts(
        self, 
        limit: Optional[int] = None, 
        order_by: Optional[PostOrderBy] = None
    ) -> List[PostType]:
        """Get posts with limit and ordering support"""
        from ..models import Posts
        
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
        """Get current listener count from latest now playing data"""
        if hasattr(self, 'latest_station_now_playing') and self.latest_station_now_playing:
            return self.latest_station_now_playing.listeners
        return None
    
    @strawberry.field
    def reviews(self) -> List[ReviewType]:
        """Placeholder for reviews - not implemented in current schema"""
        return []


@strawberry_django.type(model=StationGroups, fields="__all__")
class StationGroupType:
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