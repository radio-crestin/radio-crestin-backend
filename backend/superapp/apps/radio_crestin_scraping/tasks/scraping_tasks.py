import asyncio
import logging
from typing import List, Dict, Any
from celery import shared_task
from datetime import datetime

from ..scrapers.factory import ScraperFactory
from ..scrapers.rss_feed import RssFeedScraper
from ..services.station_service import StationService
from ..utils.data_types import StationUptimeData

logger = logging.getLogger(__name__)

print("Radio Crestin Scraping Tasks Loaded")

@shared_task(bind=True, max_retries=3)
def scrape_station_metadata(self, station_id: int) -> Dict[str, Any]:
    """Scrape metadata for a single station"""
    try:
        # Get station with metadata fetchers
        stations = StationService.get_stations_with_metadata_fetchers().filter(id=station_id)
        if not stations.exists():
            logger.warning(f"Station {station_id} not found or disabled")
            return {"success": False, "error": "Station not found or disabled"}

        station = stations.first()

        # Get metadata fetchers ordered by priority
        metadata_fetchers = station.stationsmetadatafetch_set.select_related(
            'station_metadata_fetch_category'
        ).order_by('order')

        if not metadata_fetchers.exists():
            logger.info(f"No metadata fetchers configured for station {station_id}")
            return {"success": True, "scraped_count": 0}

        # Run async scraping
        result = asyncio.run(_scrape_station_async(station, metadata_fetchers))

        logger.info(f"Scraped metadata for station {station_id}: {result}")
        return result

    except Exception as error:
        logger.error(f"Error scraping station {station_id}: {error}")
        self.retry(countdown=60 * 2**self.request.retries)


@shared_task(bind=True, max_retries=3)
def scrape_station_rss_feed(self, station_id: int) -> Dict[str, Any]:
    """Scrape RSS feed for a single station"""
    try:
        # Get station with RSS feed
        stations = StationService.get_stations_with_rss_feeds().filter(id=station_id)
        if not stations.exists():
            logger.warning(f"Station {station_id} not found, disabled, or no RSS feed")
            return {"success": False, "error": "Station not found or no RSS feed"}

        station = stations.first()

        # Run async RSS scraping
        result = asyncio.run(_scrape_rss_async(station))

        logger.info(f"Scraped RSS for station {station_id}: {result}")
        return result

    except Exception as error:
        logger.error(f"Error scraping RSS for station {station_id}: {error}")
        self.retry(countdown=60 * 2**self.request.retries)


@shared_task
def scrape_all_stations_metadata() -> Dict[str, Any]:
    """Scrape metadata for all enabled stations"""
    logger.info("Starting bulk station metadata scraping")

    try:
        stations = StationService.get_stations_with_metadata_fetchers()
        station_ids = list(stations.values_list('id', flat=True))

        if not station_ids:
            logger.info("No stations found for metadata scraping")
            return {"success": True, "total_stations": 0, "queued_tasks": 0}

        # Queue individual station tasks for parallel processing
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
        return {"success": False, "error": str(error)}


@shared_task
def scrape_all_stations_rss_feeds() -> Dict[str, Any]:
    """Scrape RSS feeds for all stations that have them"""
    logger.info("Starting bulk station RSS feed scraping")

    try:
        stations = StationService.get_stations_with_rss_feeds()
        station_ids = list(stations.values_list('id', flat=True))

        if not station_ids:
            logger.info("No stations found with RSS feeds")
            return {"success": True, "total_stations": 0, "queued_tasks": 0}

        # Queue individual RSS tasks for parallel processing
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
        return {"success": False, "error": str(error)}


@shared_task
def cleanup_old_scraped_data(days_to_keep: int = 30) -> Dict[str, Any]:
    """Clean up old station data"""
    logger.info(f"Starting cleanup of data older than {days_to_keep} days")

    try:
        success = StationService.delete_old_data(days_to_keep)
        if success:
            logger.info("Data cleanup completed successfully")
            return {"success": True, "days_kept": days_to_keep}
        else:
            return {"success": False, "error": "Cleanup failed"}

    except Exception as error:
        logger.error(f"Error during data cleanup: {error}")
        return {"success": False, "error": str(error)}


# Async helper functions

async def _scrape_station_async(station, metadata_fetchers) -> Dict[str, Any]:
    """Async function to scrape station metadata"""
    merged_data = None
    scraped_count = 0
    errors = []

    for fetcher in metadata_fetchers:
        try:
            category_slug = fetcher.station_metadata_fetch_category.slug
            scraper = ScraperFactory.get_scraper(category_slug)

            if not scraper:
                logger.warning(f"No scraper available for category: {category_slug}")
                continue

            # Scrape data
            scrape_result = await scraper.scrape(fetcher.url)

            if scraped_count == 0:
                merged_data = scrape_result
            else:
                # Merge data (prefer non-null values from new data)
                merged_data = _merge_station_data(merged_data, scrape_result)

            scraped_count += 1

        except Exception as error:
            logger.error(f"Error scraping {fetcher.url}: {error}")
            errors.append(str(error))

    # Save merged data to database
    success = False
    if merged_data:
        success = StationService.upsert_station_now_playing(station.id, merged_data)

        # Also update uptime data (simplified - always mark as up for now)
        uptime_data = StationUptimeData(
            timestamp=datetime.now().isoformat(),
            is_up=True,
            latency_ms=0,
            raw_data=[]
        )
        StationService.upsert_station_uptime(station.id, uptime_data)

    return {
        "success": success,
        "station_id": station.id,
        "scraped_count": scraped_count,
        "errors": errors
    }


async def _scrape_rss_async(station) -> Dict[str, Any]:
    """Async function to scrape station RSS feed"""
    try:
        rss_scraper = RssFeedScraper()
        rss_data = await rss_scraper.scrape_rss_feed(station.rss_feed)

        success = StationService.upsert_station_posts(station.id, rss_data)

        return {
            "success": success,
            "station_id": station.id,
            "posts_count": len(rss_data.posts)
        }

    except Exception as error:
        logger.error(f"Error scraping RSS for station {station.id}: {error}")
        return {
            "success": False,
            "station_id": station.id,
            "error": str(error)
        }


def _merge_station_data(base_data, new_data):
    """Merge two StationNowPlayingData objects, preferring non-null values"""
    # Merge raw_data arrays
    if new_data.raw_data:
        base_data.raw_data.extend(new_data.raw_data)

    # Merge error arrays
    if new_data.error:
        base_data.error.extend(new_data.error)

    # Prefer non-null values from new_data
    if new_data.current_song and new_data.current_song.name:
        base_data.current_song = new_data.current_song

    if new_data.listeners is not None:
        base_data.listeners = new_data.listeners

    # Update timestamp to latest
    base_data.timestamp = new_data.timestamp

    return base_data
