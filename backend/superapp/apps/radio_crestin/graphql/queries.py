from __future__ import annotations

import strawberry
import strawberry_django
from typing import List, Optional
from django.db.models import Prefetch

from .types import StationType, StationGroupType
from ..models import Stations, StationGroups, StationStreams, Posts, StationsUptime, StationsNowPlaying, StationToStationGroup


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
        order_by: Optional[str] = None,
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
                queryset=StationStreams.objects.filter(
                    station__disabled=False
                ).order_by('order', 'id')
            ),
            # Prefetch latest post only (limit 1, ordered by published desc)
            Prefetch(
                'posts',
                queryset=Posts.objects.order_by('-published')[:1]
            )
        ).filter(disabled=False)
        
        # Apply ordering - default to order asc, title asc for Hasura compatibility
        if order_by:
            # Parse order_by string (e.g., "order:asc,title:asc")
            order_fields = []
            for field in order_by.split(','):
                if ':' in field:
                    field_name, direction = field.strip().split(':')
                    if direction.lower() == 'desc':
                        order_fields.append(f'-{field_name}')
                    else:
                        order_fields.append(field_name)
                else:
                    order_fields.append(field.strip())
            queryset = queryset.order_by(*order_fields)
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
        order_by: Optional[str] = None,
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
            for field in order_by.split(','):
                if ':' in field:
                    field_name, direction = field.strip().split(':')
                    if direction.lower() == 'desc':
                        order_fields.append(f'-{field_name}')
                    else:
                        order_fields.append(field_name)
                else:
                    order_fields.append(field.strip())
            queryset = queryset.order_by(*order_fields)
        else:
            # Default ordering
            queryset = queryset.order_by('order', 'name')
            
        # Apply pagination
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
            
        return queryset