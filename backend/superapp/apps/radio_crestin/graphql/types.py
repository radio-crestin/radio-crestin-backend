from __future__ import annotations

import strawberry
import strawberry_django
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
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


@strawberry_django.type(model="radio_crestin.Artists", fields="__all__")
class ArtistType:
    pass


@strawberry_django.type(model="radio_crestin.Songs", fields="__all__")
class SongType:
    artist: Optional[ArtistType] = strawberry_django.field()


@strawberry_django.type(model="radio_crestin.StationStreams", fields="__all__")
class StationStreamType:
    pass


@strawberry_django.type(model="radio_crestin.Posts", fields="__all__")
class PostType:
    pass


@strawberry_django.type(model="radio_crestin.StationsUptime", fields="__all__")
class StationUptimeType:
    pass


@strawberry_django.type(model="radio_crestin.StationsNowPlaying", fields="__all__")
class StationNowPlayingType:
    song: Optional[SongType] = strawberry_django.field()


@strawberry_django.type(model="radio_crestin.StationToStationGroup", fields="__all__")
class StationToStationGroupType:
    pass


@strawberry_django.type(model="radio_crestin.Stations", fields="__all__")
class StationType:
    # Related fields optimized for the Hasura query
    station_streams: List[StationStreamType] = strawberry_django.field()
    posts: List[PostType] = strawberry_django.field()
    uptime: Optional[StationUptimeType] = strawberry_django.field(field_name="latest_station_uptime")
    now_playing: Optional[StationNowPlayingType] = strawberry_django.field(field_name="latest_station_now_playing")
    
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


@strawberry_django.type(model="radio_crestin.StationGroups", fields="__all__")
class StationGroupType:
    station_to_station_groups: List[StationToStationGroupType] = strawberry_django.field(field_name="stationtostationgroup_set")


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