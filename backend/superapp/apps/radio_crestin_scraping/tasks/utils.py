import logging
import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime
from django.utils import timezone
import httpx
import ssl

from ..utils.data_types import StationNowPlayingData, SongData

logger = logging.getLogger(__name__)


def run_scraper(scraper: Any, fetcher: Any) -> Optional[Dict[str, Any]]:
    """
    Run a scraper synchronously with proper error handling.
    
    Args:
        scraper: The scraper instance
        fetcher: The metadata fetcher configuration
        
    Returns:
        Scraped data dictionary or None if failed
    """
    try:
        # Check if this is a stream scraper that needs special handling
        if hasattr(scraper, 'get_scraper_type') and scraper.get_scraper_type() == 'stream_id3':
            # Handle async stream scrapers
            loop = _get_or_create_event_loop()
            result = loop.run_until_complete(scraper.scrape(fetcher.url, config=fetcher))
        else:
            # Handle regular HTTP scrapers
            result = _scrape_http_content(scraper, fetcher)
        
        # Convert result to serializable format
        return _serialize_scrape_result(result)
        
    except Exception as e:
        logger.error(f"Error running scraper for {fetcher.url}: {e}")
        return None


def merge_metadata_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple scraping results by priority.
    
    Args:
        results: List of result dictionaries with priority and data
        
    Returns:
        Dict with 'results' key containing merged data
    """
    if not results:
        return {"results": {"merged_data": {"current_song": {"name": "", "artist": "", "thumbnail_url": ""}}}}
    
    # Sort by priority (higher number = higher priority)
    sorted_results = sorted(results, key=lambda x: x['priority'], reverse=True)
    
    # Initialize merged data
    merged_song = {
        "name": "",
        "artist": "",
        "thumbnail_url": ""
    }
    
    # Fill fields from highest to lowest priority
    for result in sorted_results:
        data = result.get('data', {})
        song = data.get('current_song', {})
        
        # Fill empty fields only
        if not merged_song['name'] and song.get('name'):
            merged_song['name'] = song['name']
            
        if not merged_song['artist'] and song.get('artist'):
            merged_song['artist'] = song['artist']
            
        if not merged_song['thumbnail_url'] and song.get('thumbnail_url'):
            merged_song['thumbnail_url'] = song['thumbnail_url']
    
    return {
        "results": {
            "merged_data": {
                "current_song": merged_song
            }
        }
    }


def _get_or_create_event_loop():
    """Get or create an event loop for async operations."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _scrape_http_content(scraper: Any, fetcher: Any) -> Any:
    """Scrape content via HTTP with proper headers and timeout."""
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Configure timeout
    timeout = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
    
    with httpx.Client(timeout=timeout, verify=False, follow_redirects=True) as client:
        # Check content type first
        try:
            head_response = client.head(fetcher.url)
            content_type = head_response.headers.get('content-type', '').lower()
            
            # Skip audio content for HTML scrapers
            if ('audio' in content_type and 
                hasattr(scraper, 'get_scraper_type') and 
                'html' in scraper.get_scraper_type()):
                logger.warning(
                    f"Skipping HTML scraper for audio content from {fetcher.url}"
                )
                return None
        except Exception as e:
            logger.debug(f"HEAD request failed for {fetcher.url}: {e}")
        
        # Fetch content
        response = client.get(fetcher.url)
        response.raise_for_status()
        
        return scraper.extract_data(response.text, config=fetcher)


def _serialize_scrape_result(result: Any) -> Optional[Dict[str, Any]]:
    """Convert scrape result to serializable dictionary."""
    try:
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        elif hasattr(result, '__dict__'):
            return result.__dict__.copy()
        elif isinstance(result, dict):
            return result
        else:
            return {"data": str(result)}
    except Exception as e:
        logger.error(f"Could not serialize scrape result: {e}")
        return None


def _create_station_data(data_dict: Dict[str, Any]) -> Optional[StationNowPlayingData]:
    """Create StationNowPlayingData from dictionary."""
    try:
        # Extract song data if present
        current_song = None
        if 'current_song' in data_dict and data_dict['current_song']:
            song_data = data_dict['current_song']
            if isinstance(song_data, dict):
                current_song = SongData(
                    name=song_data.get('name', ''),
                    artist=song_data.get('artist', ''),
                    thumbnail_url=song_data.get('thumbnail_url', '')
                )
        
        return StationNowPlayingData(
            timestamp=data_dict.get('timestamp', timezone.now().isoformat()),
            current_song=current_song,
            listeners=data_dict.get('listeners'),
            raw_data=data_dict.get('raw_data', []),
            error=data_dict.get('error', [])
        )
        
    except Exception as e:
        logger.error(f"Could not create station data: {e}")
        return None


def _merge_station_data(
    base: StationNowPlayingData, 
    additional: StationNowPlayingData
) -> StationNowPlayingData:
    """Merge two StationNowPlayingData objects, filling missing fields."""
    # Fill current_song if missing
    if not base.current_song and additional.current_song:
        base.current_song = additional.current_song
    elif base.current_song and additional.current_song:
        # Fill missing fields in current song
        if not base.current_song.artist and additional.current_song.artist:
            base.current_song.artist = additional.current_song.artist
        if not base.current_song.name and additional.current_song.name:
            base.current_song.name = additional.current_song.name
        if not base.current_song.thumbnail_url and additional.current_song.thumbnail_url:
            base.current_song.thumbnail_url = additional.current_song.thumbnail_url
    
    # Fill listeners if missing
    if base.listeners is None and additional.listeners is not None:
        base.listeners = additional.listeners
    
    # Merge raw_data arrays
    if additional.raw_data:
        base.raw_data.extend(additional.raw_data)
    
    # Merge error arrays
    if additional.error:
        base.error.extend(additional.error)
    
    return base