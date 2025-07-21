import logging
from typing import List, Dict, Any, Optional, Union
from django.db.models import QuerySet, Q
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Concat
from django.db.models import Value

from ..models import Songs, Artists

logger = logging.getLogger(__name__)


class AutocompleteService:
    """Service layer for fast autocomplete operations using trigram indexes"""

    @staticmethod
    def search_artists(query: str, limit: int = 10) -> QuerySet[Artists]:
        """
        Fast artist search using trigram similarity with GIN indexes
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            QuerySet of Artists ordered by relevance
        """
        if not query or len(query.strip()) < 2:
            return Artists.objects.none()
        
        query = query.strip()
        
        # Use trigram similarity for fast fuzzy matching
        # The trigram index will be used automatically for similarity lookups
        return (
            Artists.objects
            .annotate(similarity=TrigramSimilarity('name', query))
            .filter(similarity__gt=0.1)  # Minimum similarity threshold
            .order_by('-similarity', 'name')
            [:limit]
        )

    @staticmethod 
    def search_songs(query: str, limit: int = 10, include_artist: bool = True) -> QuerySet[Songs]:
        """
        Fast song search using trigram similarity with GIN indexes
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            include_artist: Whether to include artist information in results
            
        Returns:
            QuerySet of Songs ordered by relevance
        """
        if not query or len(query.strip()) < 2:
            return Songs.objects.none()
        
        query = query.strip()
        
        # Search in both song name and artist name using trigram similarity
        queryset = (
            Songs.objects
            .annotate(
                # Song name similarity
                song_similarity=TrigramSimilarity('name', query),
                # Artist name similarity (if artist exists)
                artist_similarity=TrigramSimilarity('artist__name', query)
            )
            .filter(
                Q(song_similarity__gt=0.1) | 
                Q(artist_similarity__gt=0.1)
            )
            .order_by('-song_similarity', '-artist_similarity', 'name')
        )
        
        if include_artist:
            queryset = queryset.select_related('artist')
            
        return queryset[:limit]

    @staticmethod
    def search_songs_and_artists(
        query: str, 
        limit: int = 10,
        artists_limit: Optional[int] = None,
        songs_limit: Optional[int] = None
    ) -> Dict[str, Union[QuerySet, List]]:
        """
        Combined search for both songs and artists with configurable limits
        
        Args:
            query: Search query string
            limit: Total limit for results (distributed between songs and artists)
            artists_limit: Specific limit for artists (overrides distributed limit)
            songs_limit: Specific limit for songs (overrides distributed limit)
            
        Returns:
            Dictionary with 'artists' and 'songs' QuerySets
        """
        if not query or len(query.strip()) < 2:
            return {
                'artists': Artists.objects.none(),
                'songs': Songs.objects.none()
            }
        
        # Calculate limits if not specified
        if artists_limit is None and songs_limit is None:
            artists_limit = max(1, limit // 3)  # Give 1/3 to artists
            songs_limit = limit - artists_limit  # Rest to songs
        elif artists_limit is None:
            artists_limit = max(1, limit - songs_limit)
        elif songs_limit is None:
            songs_limit = max(1, limit - artists_limit)
        
        return {
            'artists': AutocompleteService.search_artists(query, artists_limit),
            'songs': AutocompleteService.search_songs(query, songs_limit)
        }

    @staticmethod
    def get_autocomplete_suggestions(
        query: str,
        search_type: str = 'combined',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get formatted autocomplete suggestions suitable for frontend consumption
        
        Args:
            query: Search query string  
            search_type: Type of search ('artists', 'songs', 'combined')
            limit: Maximum number of results
            
        Returns:
            List of dictionaries with formatted suggestion data
        """
        suggestions = []
        
        if search_type == 'artists':
            artists = AutocompleteService.search_artists(query, limit)
            for artist in artists:
                suggestions.append({
                    'id': artist.id,
                    'type': 'artist',
                    'label': artist.name,
                    'value': artist.name,
                    'thumbnail_url': artist.thumbnail_url,
                })
                
        elif search_type == 'songs':
            songs = AutocompleteService.search_songs(query, limit)
            for song in songs:
                artist_name = song.artist.name if song.artist else "Unknown Artist"
                suggestions.append({
                    'id': song.id,
                    'type': 'song', 
                    'label': f"{song.name} - {artist_name}",
                    'value': song.name,
                    'artist_name': artist_name,
                    'artist_id': song.artist.id if song.artist else None,
                    'thumbnail_url': song.thumbnail_url,
                })
                
        else:  # combined
            results = AutocompleteService.search_songs_and_artists(query, limit)
            
            # Add artists first
            for artist in results['artists']:
                suggestions.append({
                    'id': artist.id,
                    'type': 'artist',
                    'label': artist.name,
                    'value': artist.name,
                    'thumbnail_url': artist.thumbnail_url,
                })
            
            # Add songs
            for song in results['songs']:
                artist_name = song.artist.name if song.artist else "Unknown Artist"
                suggestions.append({
                    'id': song.id,
                    'type': 'song',
                    'label': f"{song.name} - {artist_name}",
                    'value': song.name,
                    'artist_name': artist_name,
                    'artist_id': song.artist.id if song.artist else None,
                    'thumbnail_url': song.thumbnail_url,
                })
        
        return suggestions