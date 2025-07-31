from typing import List, Dict, Any
from strawberry.dataloader import DataLoader
from collections import defaultdict

from ..services.listener_analytics_service import ListenerAnalyticsService


def create_listener_count_loader() -> DataLoader[int, Dict[str, int]]:
    """
    Create a DataLoader for batching listener count queries.
    
    Returns a loader that accepts station IDs and returns dicts with:
    - 'radio_crestin': Radio Crestin platform listener count
    - 'total': Combined count from all sources
    """
    async def batch_load_listener_counts(station_ids: List[int]) -> List[Dict[str, int]]:
        # Get all stations that need data
        from ..models import Stations
        stations = list(
            Stations.objects.filter(id__in=station_ids)
            .select_related('latest_station_now_playing')
        )
        
        # Create a mapping for quick lookup
        station_map = {station.id: station for station in stations}
        
        # Get combined counts in a single query
        counts = ListenerAnalyticsService.get_combined_listener_counts(
            stations=stations,
            minutes=1
        )
        
        # Return results in the same order as requested
        return [
            counts.get(station_id, {'radio_crestin': 0, 'total': 0})
            for station_id in station_ids
        ]
    
    return DataLoader(load_fn=batch_load_listener_counts)


def create_posts_loader(limit: int = 1) -> DataLoader[int, List[Any]]:
    """
    Create a DataLoader for batching posts queries with limit support.
    
    Returns a loader that accepts station IDs and returns lists of posts.
    """
    async def batch_load_posts(station_ids: List[int]) -> List[List[Any]]:
        from ..models import Posts
        from django.db.models import Window, F
        from django.db.models.functions import RowNumber
        
        # For small limits, it's more efficient to fetch all and slice in Python
        if limit <= 3:
            # Get all posts for requested stations
            posts = list(
                Posts.objects.filter(
                    station_id__in=station_ids
                ).order_by('station_id', '-published')
            )
            
            # Group by station_id and apply limit
            posts_by_station = defaultdict(list)
            for post in posts:
                if len(posts_by_station[post.station_id]) < limit:
                    posts_by_station[post.station_id].append(post)
            
            # Return in the same order as requested
            return [
                posts_by_station.get(station_id, [])
                for station_id in station_ids
            ]
        else:
            # For larger limits, use window function
            from django.db import connection
            
            # Use raw SQL with window function for efficient limited fetch per station
            with connection.cursor() as cursor:
                cursor.execute("""
                    WITH ranked_posts AS (
                        SELECT 
                            id, title, description, link, guid, published, 
                            created_at, updated_at, link_to_audio, station_id,
                            ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY published DESC) as rn
                        FROM posts
                        WHERE station_id = ANY(%s)
                    )
                    SELECT * FROM ranked_posts WHERE rn <= %s
                    ORDER BY station_id, published DESC
                """, [list(station_ids), limit])
                
                columns = [col[0] for col in cursor.description]
                posts_raw = cursor.fetchall()
            
            # Convert to Post objects and group by station
            posts_by_station = defaultdict(list)
            Post = Posts
            
            for row in posts_raw:
                post_dict = dict(zip(columns, row))
                # Remove the ranking column
                post_dict.pop('rn', None)
                
                # Create Post instance
                post = Post(
                    id=post_dict['id'],
                    title=post_dict['title'],
                    description=post_dict['description'],
                    link=post_dict['link'],
                    guid=post_dict['guid'],
                    published=post_dict['published'],
                    created_at=post_dict['created_at'],
                    updated_at=post_dict['updated_at'],
                    link_to_audio=post_dict['link_to_audio'],
                    station_id=post_dict['station_id']
                )
                post._state.adding = False
                post._state.db = 'default'
                
                posts_by_station[post.station_id].append(post)
            
            # Return in the same order as requested
            return [
                posts_by_station.get(station_id, [])
                for station_id in station_ids
            ]
    
    return DataLoader(load_fn=batch_load_posts)