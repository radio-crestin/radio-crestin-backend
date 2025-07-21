from __future__ import annotations

import strawberry
import strawberry_django
from typing import List, Optional
from django.db.models import Prefetch

from .types import StationType, StationGroupType, GetStationsResponse, OrderDirection, OrderDirectionEnum, PostOrderBy, ArtistType, SongType, PostType, ReviewType
from .filters import stations_bool_exp, stations_order_by
from ..models import Stations, StationGroups, StationStreams, Posts, StationsUptime, StationsNowPlaying, StationToStationGroup, Artists, Songs

@strawberry.input
class StationOrderBy:
    order: Optional[OrderDirectionEnum] = None
    title: Optional[OrderDirectionEnum] = None


@strawberry.type
class Query:

    @strawberry.field
    def get_stations(self) -> 'GetStationsResponse':
        """
        Exact replica of the Hasura GetStations query for backward compatibility.
        Returns both stations and station_groups in a single optimized query.
        """
        from .resolvers import get_optimized_stations_queryset, get_optimized_station_groups_queryset

        return GetStationsResponse(
            stations=list(get_optimized_stations_queryset()),
            station_groups=list(get_optimized_station_groups_queryset())
        )

    @strawberry_django.field
    def stations(
        self,
        order_by: Optional[StationOrderBy] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[StationType]:
        """
        Get stations with optimized queries for all related data.
        Maintains backward compatibility with Hasura query structure.
        """
        # Build optimized queryset with all necessary prefetches
        queryset = Stations.objects.select_related(
            'latest_station_uptime',
            'latest_station_now_playing',
            'latest_station_now_playing__song',
            'latest_station_now_playing__song__artist'
        ).prefetch_related(
            # Prefetch station streams ordered by order field
            Prefetch(
                'station_streams',
                queryset=StationStreams.objects.order_by('order', 'id')
            ),
            # Prefetch posts without slicing - the custom resolver will handle limiting
            Prefetch(
                'posts',
                queryset=Posts.objects.order_by('-published')
            )
        ).filter(disabled=False)

        # Apply ordering - default to order asc, title asc for Hasura compatibility
        if order_by:
            order_fields = []
            if order_by.order:
                if order_by.order == OrderDirection.desc:
                    order_fields.append('-order')
                else:
                    order_fields.append('order')
            if order_by.title:
                if order_by.title == OrderDirection.desc:
                    order_fields.append('-title')
                else:
                    order_fields.append('title')
            if order_fields:
                queryset = queryset.order_by(*order_fields)
            else:
                # Default Hasura ordering if no specific fields provided
                queryset = queryset.order_by('order', 'title')
        else:
            # Default Hasura ordering
            queryset = queryset.order_by('order', 'title')

        # Apply pagination
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        return queryset

    @strawberry_django.field
    def station_groups(
        self,
        order_by: Optional[StationOrderBy] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[StationGroupType]:
        """
        Get station groups with optimized queries for related station mappings.
        Maintains backward compatibility with Hasura query structure.
        """
        # Build optimized queryset
        queryset = StationGroups.objects.prefetch_related(
            # Prefetch station-to-group relationships with ordering
            Prefetch(
                'stationtostationgroup_set',
                queryset=StationToStationGroup.objects.select_related('station').order_by('order', 'station__title')
            )
        )

        # Apply ordering - default to order asc for Hasura compatibility  
        if order_by:
            order_fields = []
            if order_by.order:
                if order_by.order == OrderDirection.desc:
                    order_fields.append('-order')
                else:
                    order_fields.append('order')
            if order_by.title:  # Station groups use title field for name ordering
                if order_by.title == OrderDirection.desc:
                    order_fields.append('-name')
                else:
                    order_fields.append('name')
            if order_fields:
                queryset = queryset.order_by(*order_fields)
            else:
                # Default ordering if no specific fields provided
                queryset = queryset.order_by('order', 'name')
        else:
            # Default ordering
            queryset = queryset.order_by('order', 'name')

        # Apply pagination
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        return queryset

    # Primary key lookups (Hasura-style)
    @strawberry_django.field
    def stations_by_pk(self, id: int) -> Optional[StationType]:
        """Get station by primary key"""
        try:
            return Stations.objects.select_related(
                'latest_station_uptime',
                'latest_station_now_playing',
                'latest_station_now_playing__song',
                'latest_station_now_playing__song__artist'
            ).prefetch_related('stationstreams_set').get(id=id, disabled=False)
        except Stations.DoesNotExist:
            return None

    @strawberry_django.field
    def artists(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ArtistType]:
        """Get artists with pagination"""
        queryset = Artists.objects.all()
        
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
            
        return queryset

    @strawberry_django.field
    def artists_by_pk(self, id: int) -> Optional[ArtistType]:
        """Get artist by primary key"""
        try:
            return Artists.objects.get(id=id)
        except Artists.DoesNotExist:
            return None

    @strawberry_django.field
    def songs(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[SongType]:
        """Get songs with pagination"""
        queryset = Songs.objects.select_related('artist')
        
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
            
        return queryset

    @strawberry_django.field 
    def songs_by_pk(self, id: int) -> Optional[SongType]:
        """Get song by primary key"""
        try:
            return Songs.objects.select_related('artist').get(id=id)
        except Songs.DoesNotExist:
            return None

    @strawberry_django.field
    def posts(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PostType]:
        """Get posts with pagination"""
        queryset = Posts.objects.select_related('station').order_by('-published')
        
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
            
        return queryset

    @strawberry_django.field
    def posts_by_pk(self, id: int) -> Optional[PostType]:
        """Get post by primary key"""
        try:
            return Posts.objects.select_related('station').get(id=id)
        except Posts.DoesNotExist:
            return None

    @strawberry.field
    def health(self) -> bool:
        """Health check for GraphQL schema"""
        return True

