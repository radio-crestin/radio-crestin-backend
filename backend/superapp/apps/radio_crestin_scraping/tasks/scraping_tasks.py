import logging
import uuid
from typing import Dict, Any
from celery import shared_task
from datetime import datetime
from django.conf import settings

from ..scrapers.factory import ScraperFactory
from ..services.station_service import StationService
from ..services.task_state_service import TaskStateService
from ..utils.data_types import StationUptimeData

logger = logging.getLogger(__name__)

@shared_task
def scrape_station_metadata(station_id: int) -> Dict[str, Any]:
    """Scrape metadata for a single station"""
    # Get station with metadata fetchers
    stations = StationService.get_stations_with_metadata_fetchers().filter(id=station_id)
    if not stations.exists():
        error_msg = f"Station {station_id} not found or disabled"
        logger.error(error_msg)
        raise ValueError(error_msg)

    station = stations.first()

    # Get metadata fetchers ordered by priority
    metadata_fetchers = station.station_metadata_fetches.select_related(
        'station_metadata_fetch_category'
    ).order_by('order')

    if not metadata_fetchers.exists():
        logger.info(f"No metadata fetchers configured for station {station_id}")
        return {"success": True, "scraped_count": 0}

    # Run synchronous scraping
    result = _scrape_station_sync(station, metadata_fetchers)

    logger.info(f"Scraped metadata for station {station_id}: {result}")
    return result


@shared_task
def scrape_station_rss_feed(station_id: int) -> Dict[str, Any]:
    """Scrape RSS feed for a single station"""
    # Get station with RSS feed
    stations = StationService.get_stations_with_rss_feeds().filter(id=station_id)
    if not stations.exists():
        error_msg = f"Station {station_id} not found, disabled, or no RSS feed"
        logger.warning(error_msg)
        return {"success": True, "error": error_msg}

    station = stations.first()

    # Run synchronous RSS scraping
    result = _scrape_rss_sync(station)

    logger.info(f"Scraped RSS for station {station_id}: {result}")
    return result


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
        if settings.DEBUG:
            raise  # Re-raise the exception in debug mode for better debugging
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
        if settings.DEBUG:
            raise  # Re-raise the exception in debug mode for better debugging
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
        if settings.DEBUG:
            raise  # Re-raise the exception in debug mode for better debugging
        return {"success": False, "error": str(error)}


# Synchronous helper functions

def _scrape_station_sync(station, metadata_fetchers) -> Dict[str, Any]:
    """Synchronous function to scrape station metadata with individual fetcher processing"""
    task_id = str(uuid.uuid4())
    scraped_count = 0
    errors = []
    
    # Initialize task state
    task_init_result = TaskStateService.initialize_task_state(station.id, task_id)
    if not task_init_result['should_continue']:
        logger.info(f"Skipping station {station.id}: {task_init_result['reason']}")
        return {
            "success": False,
            "station_id": station.id,
            "scraped_count": 0,
            "errors": [task_init_result['reason']],
            "skipped": True
        }
    
    task_state = task_init_result['task_state']
    final_merged_data = None

    for fetcher in metadata_fetchers:
        try:
            category_slug = fetcher.station_metadata_fetch_category.slug
            scraper = ScraperFactory.get_scraper(category_slug)

            if not scraper:
                logger.warning(f"No scraper available for category: {category_slug}")
                error_msg = f"No scraper available for category: {category_slug}"
                TaskStateService.mark_fetcher_failed(
                    task_state, fetcher.id, fetcher.order, error_msg, task_id
                )
                errors.append(error_msg)
                continue

            # Scrape data synchronously
            try:
                # Check if this is a stream_id3 scraper that needs special handling
                if hasattr(scraper, 'get_scraper_type') and scraper.get_scraper_type() == 'stream_id3':
                    # Use the scraper's async scrape method in sync context
                    import asyncio
                    
                    # Create event loop for sync context
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run the async scrape method
                    scrape_result = loop.run_until_complete(scraper.scrape(fetcher.url))
                else:
                    # Use the original HTTP client approach for other scrapers
                    import httpx
                    import ssl

                    # Create SSL context that doesn't verify certificates
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    # Use synchronous httpx client with increased timeout
                    with httpx.Client(timeout=60, verify=False) as client:
                        response = client.get(fetcher.url)
                        response.raise_for_status()
                        scrape_result = scraper.extract_data(response.text)
            except Exception as scrape_error:
                logger.error(f"Error making HTTP request to {fetcher.url}: {scrape_error}")
                error_msg = f"HTTP request error for {fetcher.url}: {str(scrape_error)}"
                TaskStateService.mark_fetcher_failed(
                    task_state, fetcher.id, fetcher.order, error_msg, task_id
                )
                errors.append(error_msg)
                if settings.DEBUG:
                    raise
                continue

            # Process individual fetcher result and save to database immediately
            process_result = TaskStateService.process_fetcher_result(
                task_state, fetcher.id, fetcher.order, scrape_result, task_id
            )
            
            if process_result.get('should_abort'):
                logger.warning(f"Task {task_id} aborted: {process_result['reason']}")
                return {
                    "success": False,
                    "station_id": station.id,
                    "scraped_count": scraped_count,
                    "errors": errors + [process_result['reason']],
                    "aborted": True
                }
            
            if process_result['success']:
                # Save individual result to database immediately
                individual_success = StationService.upsert_station_now_playing(station.id, scrape_result)
                if individual_success:
                    scraped_count += 1
                    # Update final merged data
                    final_merged_data = process_result.get('merged_data')
                    logger.info(f"Successfully processed fetcher {fetcher.id} for station {station.id}")
                else:
                    error_msg = f"Failed to save data from fetcher {fetcher.id}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = process_result.get('reason', f'Unknown error processing fetcher {fetcher.id}')
                errors.append(error_msg)
                logger.error(error_msg)

        except Exception as error:
            logger.error(f"Error scraping {fetcher.url}: {error}")
            error_msg = f"Error scraping {fetcher.url}: {str(error)}"
            TaskStateService.mark_fetcher_failed(
                task_state, fetcher.id, fetcher.order, error_msg, task_id
            )
            errors.append(error_msg)
            if settings.DEBUG:
                raise  # Re-raise the exception in debug mode for better debugging

    # Save final merged data if available
    final_success = False
    if final_merged_data:
        final_success = StationService.upsert_station_now_playing(station.id, final_merged_data)
        
        # Also update uptime data (simplified - always mark as up for now)
        uptime_data = StationUptimeData(
            timestamp=datetime.now().isoformat(),
            is_up=True,
            latency_ms=0,
            raw_data=[]
        )
        StationService.upsert_station_uptime(station.id, uptime_data)

    # Finalize task state
    TaskStateService.finalize_task(task_state, task_id, final_success or scraped_count > 0, final_merged_data)

    return {
        "success": final_success or scraped_count > 0,
        "station_id": station.id,
        "scraped_count": scraped_count,
        "errors": errors,
        "task_id": task_id
    }


def _scrape_rss_sync(station) -> Dict[str, Any]:
    """Synchronous function to scrape station RSS feed"""
    try:
        # Simple synchronous RSS scraping
        import httpx
        import feedparser
        from datetime import datetime
        from email.utils import parsedate_to_datetime
        from ..utils.data_types import StationRssFeedData, RssFeedPost

        if not station.rss_feed:
            return {"success": True, "station_id": station.id, "posts_count": 0}

        logger.info(f"Scraping RSS feed: {station.rss_feed}")

        # Download the RSS content synchronously with browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        with httpx.Client(timeout=60, verify=False, headers=headers) as client:
            response = client.get(station.rss_feed)
            response.raise_for_status()
            rss_content = response.text

        # Parse the RSS content
        feed = feedparser.parse(rss_content)

        posts = []
        for entry in feed.entries:
            # Parse and convert date format from RFC 2822 to ISO format
            published_raw = getattr(entry, 'published', '')
            published_iso = ''
            if published_raw:
                try:
                    parsed_date = parsedate_to_datetime(published_raw)
                    published_iso = parsed_date.isoformat()
                except (ValueError, TypeError):
                    # Fallback to raw string if parsing fails
                    published_iso = published_raw

            # Simple RSS entry parsing
            post = RssFeedPost(
                title=getattr(entry, 'title', ''),
                description=getattr(entry, 'description', ''),
                link=getattr(entry, 'link', ''),
                published=published_iso
            )
            posts.append(post)

        rss_data = StationRssFeedData(posts=posts)
        success = StationService.upsert_station_posts(station.id, rss_data)

        return {
            "success": success,
            "station_id": station.id,
            "posts_count": len(rss_data.posts)
        }

    except Exception as error:
        logger.error(f"Error scraping RSS for station {station.id}: {error}")
        if settings.DEBUG:
            raise  # Re-raise the exception in debug mode for better debugging
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
