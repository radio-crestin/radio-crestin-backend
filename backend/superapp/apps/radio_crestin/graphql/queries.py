from __future__ import annotations

import strawberry
import strawberry_django
from typing import List, Optional
from django.db.models import Prefetch

from .types import StationType, StationGroupType, OrderDirection, OrderDirectionEnum, ArtistType, SongType, PostType, ReviewType
from ..models import Stations, StationGroups, StationStreams, Posts, StationToStationGroup, Artists, Songs
from ..services import AutocompleteService


@strawberry.input
class StationOrderBy:
    order: Optional[OrderDirectionEnum] = None
    title: Optional[OrderDirectionEnum] = None


@strawberry.type
class Query:
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

        Cache: This query is cached automatically by QueryCache extension.

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

        # Convert to list to execute the query
        stations_list = list(queryset)

        # Batch load listener counts for all stations
        from ..services.listener_analytics_service import ListenerAnalyticsService
        station_ids = [station.id for station in stations_list]
        listener_counts = ListenerAnalyticsService.get_combined_listener_counts(
            stations=stations_list,
            minutes=1
        )

        # Attach listener counts to stations to avoid N+1 queries
        for station in stations_list:
            if station.id in listener_counts:
                station._listener_counts_cache = listener_counts[station.id]

        # If we're not already prefetching posts, batch load latest posts for common case (limit=1)
        if not any('posts' in str(p) for p in queryset._prefetch_related_lookups):
            from ..models import Posts
            # Use raw SQL with window function for efficient single post per station
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("""
                    WITH ranked_posts AS (
                        SELECT 
                            id, title, description, link, published, 
                            created_at, updated_at, station_id,
                            ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY published DESC) as rn
                        FROM posts
                        WHERE station_id = ANY(%s)
                    )
                    SELECT * FROM ranked_posts WHERE rn = 1
                    ORDER BY station_id
                """, [station_ids])

                columns = [col[0] for col in cursor.description]
                posts_raw = cursor.fetchall()

            # Create Post objects and attach to stations
            posts_by_station = {}
            for row in posts_raw:
                post_dict = dict(zip(columns, row))
                post_dict.pop('rn', None)

                post = Posts(
                    id=post_dict['id'],
                    title=post_dict['title'],
                    description=post_dict['description'],
                    link=post_dict['link'],
                    published=post_dict['published'],
                    created_at=post_dict['created_at'],
                    updated_at=post_dict['updated_at'],
                    station_id=post_dict['station_id']
                )
                post._state.adding = False
                post._state.db = 'default'

                posts_by_station[post.station_id] = [post]

            # Attach posts to stations
            for station in stations_list:
                if station.id in posts_by_station:
                    station._posts_cache = posts_by_station[station.id]
                else:
                    # Ensure all stations have a cache entry to prevent N+1 queries
                    station._posts_cache = []

        # Batch load review stats for all stations in a single query
        from django.db.models import Avg, Count
        from ..models import Reviews as ReviewsModel

        reviews_stats = ReviewsModel.objects.filter(
            station_id__in=station_ids,
            verified=True
        ).values('station_id').annotate(
            count=Count('id'),
            avg_rating=Avg('stars')
        )

        # Build lookup dict
        reviews_stats_by_station = {
            stat['station_id']: {
                'count': stat['count'] or 0,
                'avg_rating': round(stat['avg_rating'] or 0.0, 2)
            }
            for stat in reviews_stats
        }

        # Attach review stats cache to stations
        for station in stations_list:
            station._reviews_stats_cache = reviews_stats_by_station.get(
                station.id,
                {'count': 0, 'avg_rating': 0.0}
            )

        return stations_list

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
                'station_to_station_groups',
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
            ).prefetch_related('station_streams').get(id=id, disabled=False)
        except Stations.DoesNotExist:
            return None

    @strawberry_django.field
    def artists(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[ArtistType]:
        """Get artists with pagination and search support"""
        if search:
            # Use the autocomplete service for fast trigram-based search
            return AutocompleteService.search_artists(search, limit or 10)

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
        search: Optional[str] = None,
    ) -> List[SongType]:
        """Get songs with pagination and search support"""
        if search:
            # Use the autocomplete service for fast trigram-based search
            return AutocompleteService.search_songs(search, limit or 10)

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
    def reviews(
        self,
        station_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ReviewType]:
        """
        Get verified reviews with optional filtering by station.

        Args:
            station_id: Optional station ID to filter reviews
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip

        Returns:
            List of verified reviews ordered by created_at descending
        """
        from ..models import Reviews as ReviewsModel

        queryset = ReviewsModel.objects.filter(verified=True)

        if station_id is not None:
            queryset = queryset.filter(station_id=station_id)

        queryset = queryset.order_by('-created_at')

        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        return [
            ReviewType(
                id=r.id,
                station_id=r.station_id,
                stars=r.stars,
                message=r.message,
                user_identifier=r.user_identifier,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
                verified=r.verified
            )
            for r in queryset
        ]

    @strawberry.field
    def autocomplete(
        self,
        query: str,
        search_type: Optional[str] = "combined",
        limit: Optional[int] = 10,
    ) -> List[strawberry.scalars.JSON]:
        """
        Fast autocomplete search for songs and artists using trigram indexes

        Args:
            query: Search query string
            search_type: Type of search ('artists', 'songs', 'combined')
            limit: Maximum number of results to return

        Returns:
            List of formatted autocomplete suggestions
        """
        return AutocompleteService.get_autocomplete_suggestions(
            query=query,
            search_type=search_type or "combined",
            limit=limit or 10
        )


