import json
import logging
import uuid
from typing import Dict, Any, Optional
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from ..scrapers.factory import ScraperFactory
from ..services.station_service import StationService
from .utils import run_scraper, merge_metadata_results

logger = logging.getLogger(__name__)


@shared_task(name='radio_crestin_scraping.scrape_station_metadata', time_limit=30)
def scrape_station_metadata(station_id: int) -> Dict[str, Any]:
    """
    Scrape metadata for a single station.

    Returns:
        Dict containing success status, scraped count, and any errors
    """
    from superapp.apps.radio_crestin.models import Stations

    try:
        station = Stations.objects.select_related().get(id=station_id)

        if station.disabled:
            logger.info(f"Station {station_id} is disabled - skipping")
            return {"success": True, "scraped_count": 0, "station_disabled": True}

        metadata_fetchers = station.station_metadata_fetches.select_related(
            'station_metadata_fetch_category'
        ).order_by('-priority')

        if not metadata_fetchers.exists():
            logger.info(f"No metadata fetchers configured for station {station_id}")
            return {"success": True, "scraped_count": 0}

    except Stations.DoesNotExist:
        logger.error(f"Station {station_id} not found")
        raise ValueError(f"Station {station_id} not found")

    # Execute scraping
    task_id = str(uuid.uuid4())
    results = []
    errors = []

    for fetcher in metadata_fetchers:
        try:
            scraper = ScraperFactory.get_scraper(fetcher.station_metadata_fetch_category.slug)
            if not scraper:
                logger.warning(f"No scraper available for: {fetcher.station_metadata_fetch_category.slug}")
                continue

            result = run_scraper(scraper, fetcher)
            if result:
                results.append({
                    'priority': fetcher.priority,
                    'data': result,
                    'dirty_metadata': fetcher.dirty_metadata
                })

        except Exception as e:
            error_msg = f"Error scraping {fetcher.url}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            if settings.DEBUG:
                raise

    # Merge results and save
    success = False

    if results:
        merged_result = merge_metadata_results(results)
        # Ensure merged_data is a dictionary
        merged_data_raw = merged_result.get('results', {})
        if isinstance(merged_data_raw, dict):
            merged_data = merged_data_raw.get('merged_data', {})
        else:
            merged_data = {}
        
        # Ensure merged_data is a dictionary, not a list
        if not isinstance(merged_data, dict):
            merged_data = {}

        # Create a simple data object for the service
        from ..utils.data_types import StationNowPlayingData, SongData

        song_data = merged_data.get('current_song', {}) if isinstance(merged_data, dict) else {}
        current_song = None
        
        # Try to create SongData with proper error handling
        try:
            if isinstance(song_data, dict):
                name_val = song_data.get('name')
                artist_val = song_data.get('artist')
                
                # Only proceed if we have valid name or artist data
                if name_val or artist_val:
                    # Ensure all values are strings, not lists
                    name_value = song_data.get('name', '')
                    artist_value = song_data.get('artist', '')
                    thumbnail_value = song_data.get('thumbnail_url', '')
                    
                    # Convert lists to strings if necessary
                    if isinstance(name_value, list):
                        name_value = ' '.join(str(x) for x in name_value) if name_value else ''
                    else:
                        name_value = str(name_value) if name_value else ''
                        
                    if isinstance(artist_value, list):
                        artist_value = ' '.join(str(x) for x in artist_value) if artist_value else ''
                    else:
                        artist_value = str(artist_value) if artist_value else ''
                        
                    if isinstance(thumbnail_value, list):
                        thumbnail_value = str(thumbnail_value[0]) if thumbnail_value else ''
                    else:
                        thumbnail_value = str(thumbnail_value) if thumbnail_value else ''
                    
                    current_song = SongData(
                        name=name_value,
                        artist=artist_value,
                        thumbnail_url=thumbnail_value
                    )
        except Exception as e:
            logger.error(f"Error creating SongData: {e}, song_data: {song_data}")
            current_song = None

        listeners = merged_data.get('listeners') if isinstance(merged_data, dict) else None
        error_list = merged_data.get('error', []) if isinstance(merged_data, dict) else []
        if not isinstance(error_list, list):
            error_list = []

        station_data = StationNowPlayingData(
            timestamp=timezone.now().isoformat(),
            current_song=current_song,
            listeners=listeners,
            raw_data=json.loads(json.dumps({
                'results': results,
                'merged_data': merged_data,
            }, default=str)),
            error=error_list + errors
        )

        # Determine if any successful fetcher has dirty metadata
        dirty_metadata = any(r['dirty_metadata'] for r in results)
        success = StationService.upsert_station_now_playing(
            station.id,
            station_data,
            dirty_metadata=dirty_metadata
        )

    return {
        "success": success,
        "station_id": station_id,
        "scraped_count": len(results),
        "errors": errors,
        "task_id": task_id
    }

