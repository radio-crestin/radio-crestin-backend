import logging
from typing import Dict, Any
from celery import shared_task
from django.conf import settings

from ..services.station_service import StationService
from .scrape_station_metadata import scrape_station_metadata
from .scrape_station_rss_feed import scrape_station_rss_feed

logger = logging.getLogger(__name__)


@shared_task(name='radio_crestin_scraping.scrape_all_stations_metadata', time_limit=30)
def scrape_all_stations_metadata() -> Dict[str, Any]:
    """
    Queue metadata scraping tasks for all enabled stations.
    
    Returns:
        Dict containing total stations count and queued tasks count
    """
    logger.info("Starting bulk station metadata scraping")
    
    try:
        # Get all stations with metadata fetchers
        stations = StationService.get_stations_with_metadata_fetchers()
        station_ids = list(stations.values_list('id', flat=True))
        
        if not station_ids:
            logger.info("No stations found for metadata scraping")
            return {"success": True, "total_stations": 0, "queued_tasks": 0}
        
        # Queue individual tasks for parallel processing
        for station_id in station_ids:
            scrape_station_metadata.delay(station_id)
        
        logger.info(f"Queued metadata scraping for {len(station_ids)} stations")
        return {
            "success": True,
            "total_stations": len(station_ids),
            "queued_tasks": len(station_ids)
        }
        
    except Exception as error:
        logger.error(f"Error queuing station metadata tasks: {error}")
        if settings.DEBUG:
            raise
        return {"success": False, "error": str(error)}


@shared_task(name='radio_crestin_scraping.scrape_all_stations_rss_feeds', time_limit=30)
def scrape_all_stations_rss_feeds() -> Dict[str, Any]:
    """
    Queue RSS feed scraping tasks for all stations with RSS feeds.
    
    Returns:
        Dict containing total stations count and queued tasks count
    """
    logger.info("Starting bulk station RSS feed scraping")
    
    try:
        # Get all stations with RSS feeds
        stations = StationService.get_stations_with_rss_feeds()
        station_ids = list(stations.values_list('id', flat=True))
        
        if not station_ids:
            logger.info("No stations found with RSS feeds")
            return {"success": True, "total_stations": 0, "queued_tasks": 0}
        
        # Queue individual tasks for parallel processing
        for station_id in station_ids:
            scrape_station_rss_feed.delay(station_id)
        
        logger.info(f"Queued RSS scraping for {len(station_ids)} stations")
        return {
            "success": True,
            "total_stations": len(station_ids),
            "queued_tasks": len(station_ids)
        }
        
    except Exception as error:
        logger.error(f"Error queuing RSS tasks: {error}")
        if settings.DEBUG:
            raise
        return {"success": False, "error": str(error)}