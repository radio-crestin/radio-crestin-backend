import strawberry
import strawberry_django
from typing import List, Optional
from django.db import connection
from django.db.models import Prefetch

from datetime import datetime, timedelta, timezone as dt_tz

from .types import (
    StationType, StationGroupType, OrderDirection, OrderDirectionEnum,
    ArtistType, SongType, PostType, ReviewType,
    StationMetadataType, StationMetadataUptimeType, StationMetadataNowPlayingType,
    StationMetadataSongType, StationMetadataArtistType,
    StationMetadataHistoryType, StationMetadataHistoryEntryType,
    StationStreamingConfigType, StationScraperConfigType,
)
from ..models import Stations, StationGroups, StationStreams, Posts, StationToStationGroup, Artists, Songs
from ..models import StationsNowPlayingHistory
from ..services import AutocompleteService
from ..utils.cdn_proxy import proxy_image_url


@strawberry.input
class StationOrderBy:
    order: Optional[OrderDirectionEnum] = None
    title: Optional[OrderDirectionEnum] = None


def _latest_history_per_station(station_ids, as_of_dt):
    """Fetch the latest StationsNowPlayingHistory row per station using LATERAL JOIN.

    This is O(n_stations) via index seeks on idx_snph_station_ts,
    instead of O(n_history_rows) with DISTINCT ON or correlated subqueries.
    Returns a dict {station_id: StationsNowPlayingHistory}.
    """
    if not station_ids:
        return {}

    placeholders = ','.join(['%s'] * len(station_ids))
    sql = f"""
        SELECT h.id
        FROM unnest(ARRAY[{placeholders}]::bigint[]) AS sid(station_id)
        CROSS JOIN LATERAL (
            SELECT snph.id
            FROM stations_now_playing_history snph
            WHERE snph.station_id = sid.station_id
              AND snph.timestamp <= %s
            ORDER BY snph.timestamp DESC
            LIMIT 1
        ) h
    """
    params = list(station_ids) + [as_of_dt]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        history_ids = [row[0] for row in cursor.fetchall()]

    if not history_ids:
        return {}

    records = StationsNowPlayingHistory.objects.filter(
        id__in=history_ids,
    ).select_related('song', 'song__artist')

    return {h.station_id: h for h in records}


@strawberry.type
class Query:
    @strawberry_django.field
    def stations(
        self,
        order_by: Optional[StationOrderBy] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        station_slugs: Optional[List[str]] = None,
        exclude_station_slugs: Optional[List[str]] = None,
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

        # Apply slug filters
        if station_slugs:
            queryset = queryset.filter(slug__in=station_slugs)
        if exclude_station_slugs:
            queryset = queryset.exclude(slug__in=exclude_station_slugs)

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
        station_slug: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ReviewType]:
        """
        Get verified reviews with optional filtering by station.
        At least one of station_id or station_slug is required.

        Args:
            station_id: Optional station ID to filter reviews
            station_slug: Optional station slug to filter reviews
            limit: Maximum number of reviews to return
            offset: Number of reviews to skip

        Returns:
            List of verified reviews ordered by created_at descending
        """
        from ..models import Reviews as ReviewsModel

        queryset = ReviewsModel.objects.filter(verified=True)

        if station_id is not None:
            queryset = queryset.filter(station_id=station_id)
        elif station_slug:
            station = Stations.objects.filter(slug=station_slug, disabled=False).first()
            if station:
                queryset = queryset.filter(station_id=station.id)
            else:
                return []

        queryset = queryset.order_by('-created_at')

        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        return [
            ReviewType(
                id=r.id,
                station_id=r.station_id,
                song_id=r.song_id,
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

    @strawberry.field
    def stations_metadata(
        self,
        timestamp: Optional[int] = None,
        changes_from_timestamp: Optional[int] = None,
        station_slugs: Optional[List[str]] = None,
        exclude_station_slugs: Optional[List[str]] = None,
    ) -> List[StationMetadataType]:
        """
        Lightweight station metadata - only uptime + now_playing.
        Supports historical lookups via timestamp and change detection
        via changes_from_timestamp.
        """
        from django.utils import timezone as tz
        from ..services.listener_analytics_service import ListenerAnalyticsService

        now = tz.now()
        as_of_dt = (
            datetime.fromtimestamp(timestamp, tz=dt_tz.utc)
            if timestamp else now
        )

        def _build_song_type(song):
            if not song:
                return None
            artist = None
            if song.artist:
                artist = StationMetadataArtistType(
                    id=song.artist.id,
                    name=song.artist.name,
                    thumbnail_url=proxy_image_url(song.artist.thumbnail_url, width=250, format="webp") if hasattr(song.artist, 'thumbnail_url') else None,
                )
            return StationMetadataSongType(
                id=song.id,
                name=song.name,
                thumbnail_url=proxy_image_url(song.thumbnail_url, width=250, format="webp") if hasattr(song, 'thumbnail_url') else None,
                artist=artist,
            )

        def _build_metadata(station, np_override=None, internal_listeners=None):
            # Uptime
            uptime = None
            up = getattr(station, 'latest_station_uptime', None)
            if up:
                uptime = StationMetadataUptimeType(
                    is_up=up.is_up,
                    latency_ms=up.latency_ms,
                    timestamp=up.timestamp.isoformat() if up.timestamp else '',
                )

            # Now playing. The `listeners` field combines the upstream-reported
            # count (when the station's stats endpoint exposes one) with
            # radio-crestin's own active-session count, so stations whose
            # upstream has no public stats endpoint (e.g. RadioBoss-hosted)
            # still surface a listener count instead of NULL.
            # Historical lookups (`timestamp` mode) skip the radio-crestin
            # addition because internal counts are point-in-time-now only.
            def _combined_listeners(upstream):
                if internal_listeners is None:
                    return upstream
                if upstream is None and internal_listeners == 0:
                    return None
                return (upstream or 0) + internal_listeners

            now_playing = None
            if np_override is not None:
                # Use historical record
                now_playing = StationMetadataNowPlayingType(
                    timestamp=np_override.timestamp.isoformat(),
                    listeners=_combined_listeners(np_override.listeners),
                    song=_build_song_type(np_override.song),
                )
            else:
                np = getattr(station, 'latest_station_now_playing', None)
                if np:
                    now_playing = StationMetadataNowPlayingType(
                        timestamp=np.timestamp.isoformat(),
                        listeners=_combined_listeners(np.listeners),
                        song=_build_song_type(np.song),
                    )

            return StationMetadataType(
                id=station.id,
                slug=station.slug,
                title=station.title,
                uptime=uptime,
                now_playing=now_playing,
            )

        # Build base station filter kwargs
        station_filter = {'disabled': False}
        station_exclude = {}
        if station_slugs:
            station_filter['slug__in'] = station_slugs
        if exclude_station_slugs:
            station_exclude['slug__in'] = exclude_station_slugs

        # Mode 1: changes_from_timestamp — only return stations with changes
        if changes_from_timestamp is not None:
            changes_from_dt = datetime.fromtimestamp(
                changes_from_timestamp, tz=dt_tz.utc
            )

            # Query 1: index-only scan on idx_snph_ts_station
            changed_ids = set(
                StationsNowPlayingHistory.objects.filter(
                    timestamp__gt=changes_from_dt,
                    timestamp__lte=as_of_dt,
                ).values_list('station_id', flat=True).distinct()
            )

            if not changed_ids:
                return []

            # Query 2: load those stations
            qs = Stations.objects.filter(
                id__in=changed_ids, **station_filter,
            ).select_related(
                'latest_station_uptime',
            )
            if station_exclude:
                qs = qs.exclude(**station_exclude)
            stations = list(qs)

            station_ids = [s.id for s in stations]

            # Query 3: latest history per station via LATERAL JOIN (O(n_stations))
            history_by_station = _latest_history_per_station(station_ids, as_of_dt)

            # Internal listener counts (point-in-time-now only — relevant
            # because `changes_from_timestamp` polling returns *current*
            # state for stations that changed, not historical playback).
            internal_counts = ListenerAnalyticsService.get_batch_listener_counts(
                station_ids, minutes=1,
            )

            return [
                _build_metadata(
                    s,
                    np_override=history_by_station.get(s.id),
                    internal_listeners=internal_counts.get(s.id, 0),
                )
                for s in stations
            ]

        # Mode 2: timestamp only — all stations with historical now_playing.
        # Historical playback intentionally does NOT add radio-crestin's
        # current-session count.
        if timestamp is not None:
            qs = Stations.objects.filter(**station_filter).select_related(
                'latest_station_uptime',
            ).order_by('order', 'title')
            if station_exclude:
                qs = qs.exclude(**station_exclude)
            stations = list(qs)

            station_ids = [s.id for s in stations]

            # Latest history per station via LATERAL JOIN (O(n_stations))
            history_by_station = _latest_history_per_station(station_ids, as_of_dt)

            return [
                _build_metadata(s, np_override=history_by_station.get(s.id))
                for s in stations
            ]

        # Mode 3: default — current data
        qs = Stations.objects.filter(**station_filter).select_related(
            'latest_station_uptime',
            'latest_station_now_playing',
            'latest_station_now_playing__song',
            'latest_station_now_playing__song__artist',
        ).order_by('order', 'title')
        if station_exclude:
            qs = qs.exclude(**station_exclude)
        stations = list(qs)
        station_ids = [s.id for s in stations]

        internal_counts = ListenerAnalyticsService.get_batch_listener_counts(
            station_ids, minutes=1,
        )
        return [
            _build_metadata(s, internal_listeners=internal_counts.get(s.id, 0))
            for s in stations
        ]

    @strawberry.field
    def stations_metadata_history(
        self,
        station_slug: str,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
    ) -> StationMetadataHistoryType:
        """
        Historical metadata for a station in a time range (max 24h).
        Defaults: from_timestamp = now - 1 hour, to_timestamp = now.
        """
        from django.utils import timezone as tz

        now_ts = int(tz.now().timestamp())

        # Default to_timestamp to current time
        if to_timestamp is None or to_timestamp == 0:
            to_timestamp = now_ts

        # Default from_timestamp to 1 hour ago
        if from_timestamp is None or from_timestamp == 0:
            from_timestamp = now_ts - 3600

        # Validation: max 24h range
        if to_timestamp - from_timestamp > 86400:
            raise ValueError("Time range cannot exceed 24 hours (86400 seconds).")

        # Validation: to_timestamp not in the future (+ 2s tolerance)
        if to_timestamp > now_ts + 2:
            raise ValueError("to_timestamp cannot be in the future.")

        from_dt = datetime.fromtimestamp(from_timestamp, tz=dt_tz.utc)
        to_dt = datetime.fromtimestamp(to_timestamp, tz=dt_tz.utc)

        # Query 1: find station
        station = Stations.objects.filter(
            slug=station_slug, disabled=False,
        ).first()
        if not station:
            raise ValueError(f"Station '{station_slug}' not found.")

        # Query 2: fetch history records, deduplicated to song changes only.
        # We fetch all rows in the time range ordered by timestamp, then keep
        # only rows where the song_id differs from the previous row.
        records = list(
            StationsNowPlayingHistory.objects.filter(
                station=station,
                timestamp__gte=from_dt,
                timestamp__lte=to_dt,
            ).select_related('song', 'song__artist').order_by('timestamp')
        )

        # Deduplicate: keep only entries where song changed from the previous entry
        deduplicated = []
        prev_song_id = None
        for r in records:
            current_song_id = r.song_id
            if current_song_id != prev_song_id:
                deduplicated.append(r)
                prev_song_id = current_song_id

        def _build_song(song):
            if not song:
                return None
            artist = None
            if song.artist:
                artist = StationMetadataArtistType(
                    id=song.artist.id,
                    name=song.artist.name,
                    thumbnail_url=proxy_image_url(song.artist.thumbnail_url, width=250, format="webp") if hasattr(song.artist, 'thumbnail_url') else None,
                )
            return StationMetadataSongType(
                id=song.id,
                name=song.name,
                thumbnail_url=proxy_image_url(song.thumbnail_url, width=250, format="webp") if hasattr(song, 'thumbnail_url') else None,
                artist=artist,
            )

        history = [
            StationMetadataHistoryEntryType(
                timestamp=r.timestamp.isoformat(),
                listeners=r.listeners,
                song=_build_song(r.song),
            )
            for r in deduplicated
        ]

        return StationMetadataHistoryType(
            station_id=station.id,
            station_slug=station.slug,
            station_title=station.title,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            count=len(history),
            history=history,
        )

    @strawberry.field
    def streaming_station_configs(
        self,
        info: strawberry.Info,
        station_slugs: Optional[List[str]] = None,
    ) -> List[StationStreamingConfigType]:
        """Get station streaming configs for pod bootstrap.
        Protected by X-Streaming-Api-Key header."""
        import os
        request = info.context.request
        api_key = request.headers.get('X-Streaming-Api-Key', '')
        expected_key = os.getenv('STREAMING_POD_API_KEY', '')
        if not expected_key or api_key != expected_key:
            raise PermissionError("Invalid streaming pod API key")

        qs = Stations.objects.filter(
            disabled=False, transcode_enabled=True
        ).prefetch_related(
            'station_metadata_fetches__station_metadata_fetch_category'
        ).order_by('station_order', 'title')

        if station_slugs:
            qs = qs.filter(slug__in=station_slugs)

        results = []
        for station in qs:
            scrapers = [
                StationScraperConfigType(
                    category_slug=f.station_metadata_fetch_category.slug,
                    url=f.url,
                    priority=f.priority,
                    dirty_metadata=f.dirty_metadata,
                    split_character=f.split_character,
                    station_name_regex=str(f.station_name_regex) if f.station_name_regex else None,
                    artist_regex=str(f.artist_regex) if f.artist_regex else None,
                    title_regex=str(f.title_regex) if f.title_regex else None,
                )
                for f in station.station_metadata_fetches.all()
            ]
            results.append(StationStreamingConfigType(
                station_id=station.id,
                slug=station.slug,
                title=station.title,
                stream_url=station.stream_url,
                transcode_enabled=station.transcode_enabled,
                metadata_timestamp_source=station.metadata_timestamp_source,
                metadata_scrape_interval=station.metadata_scrape_interval,
                id3_metadata_delay_offset=station.id3_metadata_delay_offset,
                config_version=station.config_version,
                scrapers=scrapers,
            ))
        return results


