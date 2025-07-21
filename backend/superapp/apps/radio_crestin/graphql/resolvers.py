from __future__ import annotations

import strawberry
from typing import List, Optional
from django.db.models import Prefetch, Q

from .types import StationType, StationGroupType
from ..models import (
    Stations, StationGroups, StationStreams, Posts, 
    StationsUptime, StationsNowPlaying, StationToStationGroup
)


@strawberry.type
class GetStationsQuery:
    """
    Exact replica of the Hasura GetStations query structure for backward compatibility.
    Optimized for minimal database queries and maximum performance.
    """
    
    @strawberry.field
    def stations(self) -> List[StationType]:
        """
        Optimized query that replicates the exact Hasura query structure:
        - Ordered by {order: asc, title: asc}
        - Includes all related data with minimal queries
        - Maintains field name compatibility
        """
        return Stations.objects.select_related(
            # Single query joins for foreign keys
            'latest_station_uptime',
            'latest_station_now_playing',
            'latest_station_now_playing__song',
            'latest_station_now_playing__song__artist'
        ).prefetch_related(
            # Optimized prefetch for station_streams ordered by order field
            Prefetch(
                'station_streams',
                queryset=StationStreams.objects.order_by('order').select_related()
            ),
            # Prefetch posts without slicing - the custom resolver will handle limiting
            Prefetch(
                'posts',
                queryset=Posts.objects.order_by('-published')
            )
        ).filter(
            disabled=False
        ).order_by('order', 'title')
    
    @strawberry.field
    def station_groups(self) -> List[StationGroupType]:
        """
        Optimized query for station groups with related station mappings.
        Maintains exact Hasura field structure and ordering.
        """
        return StationGroups.objects.prefetch_related(
            # Optimized prefetch for station-to-group relationships
            Prefetch(
                'station_to_station_groups',
                queryset=StationToStationGroup.objects.select_related('station').order_by('order')
            )
        ).order_by('order', 'name')


def get_optimized_stations_queryset():
    """
    Utility function that returns the most optimized queryset for stations.
    This reduces the query count to the absolute minimum while maintaining
    all the data needed for the Hasura compatibility.
    
    Query optimization breakdown:
    - 1 query for stations with select_related joins
    - 1 query for all station_streams (prefetch_related)  
    - 1 query for posts (prefetch_related, limiting handled by resolver)
    - Total: 3 queries instead of N+1 queries
    """
    return Stations.objects.select_related(
        'latest_station_uptime',
        'latest_station_now_playing', 
        'latest_station_now_playing__song',
        'latest_station_now_playing__song__artist'
    ).prefetch_related(
        Prefetch(
            'station_streams',
            queryset=StationStreams.objects.order_by('order')
        ),
        Prefetch(
            'posts', 
            queryset=Posts.objects.order_by('-published')
        )
    ).filter(disabled=False).order_by('order', 'title')


def get_optimized_station_groups_queryset():
    """
    Utility function for optimized station groups query.
    
    Query optimization breakdown:
    - 1 query for station groups
    - 1 query for all station-to-group relationships with stations
    - Total: 2 queries instead of N+1 queries
    """
    return StationGroups.objects.prefetch_related(
        Prefetch(
            'station_to_station_groups',
            queryset=StationToStationGroup.objects.select_related('station').order_by('order')
        )
    ).order_by('order', 'name')