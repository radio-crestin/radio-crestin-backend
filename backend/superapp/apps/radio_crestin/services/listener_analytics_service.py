from typing import Dict, List, Optional
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from collections import defaultdict

from ..models import ListeningSessions, Stations


class ListenerAnalyticsService:
    """
    Service for efficiently calculating listener analytics.
    Provides batch loading capabilities to avoid N+1 queries.
    """
    
    @classmethod
    def get_batch_listener_counts(
        cls,
        station_ids: List[int],
        minutes: int = 1
    ) -> Dict[int, int]:
        """
        Get listener counts for multiple stations in a single query.
        
        Args:
            station_ids: List of station IDs
            minutes: Activity window in minutes (default: 1)
            
        Returns:
            Dict mapping station_id to listener count
        """
        activity_threshold = timezone.now() - timedelta(minutes=minutes)
        
        # Get all active sessions for the requested stations
        session_data = (
            ListeningSessions.objects
            .filter(
                station_id__in=station_ids,
                is_active=True,
                last_activity__gte=activity_threshold
            )
            .values('station_id')
            .annotate(
                unique_listeners=Count(
                    'id',
                    distinct=True,
                    filter=Q(user__isnull=False) | Q(anonymous_session_id__isnull=False)
                )
            )
        )
        
        # Convert to dict for O(1) lookups
        counts = {item['station_id']: item['unique_listeners'] for item in session_data}
        
        # Ensure all requested stations have an entry (default to 0)
        for station_id in station_ids:
            if station_id not in counts:
                counts[station_id] = 0
                
        return counts
    
    @classmethod
    def get_all_station_listener_counts(cls, minutes: int = 1) -> Dict[int, int]:
        """
        Get listener counts for all active stations in a single query.
        
        Args:
            minutes: Activity window in minutes (default: 1)
            
        Returns:
            Dict mapping station_id to listener count
        """
        activity_threshold = timezone.now() - timedelta(minutes=minutes)
        
        # Use raw SQL for optimal performance with proper distinct counting
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    station_id,
                    COUNT(DISTINCT COALESCE(user_id::text, '') || '-' || anonymous_session_id) as listener_count
                FROM listening_sessions
                WHERE 
                    is_active = true 
                    AND last_activity >= %s
                GROUP BY station_id
            """, [activity_threshold])
            
            results = cursor.fetchall()
            
        return {station_id: count for station_id, count in results}
    
    @classmethod
    def get_combined_listener_counts(
        cls,
        stations: List[Stations],
        minutes: int = 1
    ) -> Dict[int, Dict[str, int]]:
        """
        Get both radio-crestin and total listener counts for multiple stations.
        
        Args:
            stations: List of Station objects
            minutes: Activity window in minutes
            
        Returns:
            Dict mapping station_id to {'radio_crestin': count, 'total': count}
        """
        # Get radio-crestin counts in batch
        radio_crestin_counts = cls.get_all_station_listener_counts(minutes=minutes)
        
        # Build result dict
        result = {}
        for station in stations:
            station_id = station.id
            radio_crestin_count = radio_crestin_counts.get(station_id, 0)
            
            # Get external count from now playing data if available
            external_count = 0
            if hasattr(station, 'latest_station_now_playing') and station.latest_station_now_playing:
                external_count = station.latest_station_now_playing.listeners or 0
            
            result[station_id] = {
                'radio_crestin': radio_crestin_count,
                'total': radio_crestin_count + external_count
            }
            
        return result