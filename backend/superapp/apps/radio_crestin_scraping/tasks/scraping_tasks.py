import logging
import uuid
from typing import Dict, Any
from celery import shared_task
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from dateutil.parser import parse

from ..scrapers.factory import ScraperFactory
from ..services.station_service import StationService

logger = logging.getLogger(__name__)

@shared_task(time_limit=30)
def scrape_station_metadata(station_id: int) -> Dict[str, Any]:
    """Scrape metadata for a single station"""
    # Get station with metadata fetchers
    stations = StationService.get_stations_with_metadata_fetchers().filter(id=station_id)
    if not stations.exists():
        error_msg = f"Station {station_id} not found or disabled"
        logger.error(error_msg)
        raise ValueError(error_msg)

    station = stations.first()

    # Get metadata fetchers ordered by priority (higher number = higher priority)
    metadata_fetchers = station.station_metadata_fetches.select_related(
        'station_metadata_fetch_category'
    ).order_by('-priority')

    if not metadata_fetchers.exists():
        logger.info(f"No metadata fetchers configured for station {station_id}")
        return {"success": True, "scraped_count": 0}

    # Run synchronous scraping
    result = _scrape_station_sync(station, metadata_fetchers)

    logger.info(f"Scraped metadata for station {station_id}: {result}")
    return result


@shared_task(time_limit=120)
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


@shared_task(time_limit=30)
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


@shared_task(time_limit=30)
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


@shared_task
def cleanup_old_dirty_metadata(days_to_keep: int = 7) -> Dict[str, Any]:
    """Clean up old songs and artists marked as dirty metadata"""
    from datetime import timedelta
    from django.utils import timezone
    from superapp.apps.radio_crestin.models import Songs, Artists

    logger.info(f"Starting cleanup of dirty metadata older than {days_to_keep} days")

    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Delete old dirty songs
        songs_deleted = Songs.objects.filter(
            dirty_metadata=True,
            created_at__lt=cutoff_date
        ).delete()

        # Delete old dirty artists that are no longer referenced by any songs
        artists_deleted = Artists.objects.filter(
            dirty_metadata=True,
            created_at__lt=cutoff_date,
            songs__isnull=True  # Not referenced by any songs
        ).delete()

        logger.info(f"Deleted {songs_deleted[0]} dirty songs and {artists_deleted[0]} dirty artists")

        return {
            "success": True,
            "days_kept": days_to_keep,
            "songs_deleted": songs_deleted[0],
            "artists_deleted": artists_deleted[0]
        }

    except Exception as error:
        logger.error(f"Error during dirty metadata cleanup: {error}")
        if settings.DEBUG:
            raise  # Re-raise the exception in debug mode for better debugging
        return {"success": False, "error": str(error)}


# Synchronous helper functions

def _scrape_station_sync(station, metadata_fetchers) -> Dict[str, Any]:
    """Synchronous function to scrape station metadata with simplified state tracking"""
    task_id = str(uuid.uuid4())
    task_start_time = timezone.now()
    scraped_count = 0
    errors = []

    # Get current station data to check existing raw_data
    current_data = None
    if hasattr(station, 'now_playing') and station.now_playing:
        current_data = station.now_playing

    # Raw data will store state of each metadata fetch with timestamps
    fetcher_states = {}
    final_merged_data = None

    for fetcher in metadata_fetchers:
        try:
            category_slug = fetcher.station_metadata_fetch_category.slug
            scraper = ScraperFactory.get_scraper(category_slug)

            if not scraper:
                logger.warning(f"No scraper available for category: {category_slug}")
                error_msg = f"No scraper available for category: {category_slug}"

                # Mark fetcher as failed in state
                fetcher_states[str(fetcher.id)] = {
                    'fetcher_id': fetcher.id,
                    'category_slug': category_slug,
                    'priority': fetcher.priority,
                    'status': 'failed',
                    'error': error_msg,
                    'timestamp': task_start_time.isoformat(),
                    'task_id': task_id
                }

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

                    # Run the async scrape method with config
                    scrape_result = loop.run_until_complete(scraper.scrape(fetcher.url, config=fetcher))
                else:
                    # Use the original HTTP client approach for other scrapers
                    import httpx
                    import ssl

                    # Create SSL context that doesn't verify certificates
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    # Use synchronous httpx client with 5 second timeout for non-stream scrapers
                    timeout = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
                    with httpx.Client(timeout=timeout, verify=False, follow_redirects=True) as client:
                        # First check content type with HEAD request to avoid downloading streams
                        try:
                            head_response = client.head(fetcher.url)
                            content_type = head_response.headers.get('content-type', '').lower()

                            # Skip if this is audio content being passed to HTML scraper
                            if 'audio' in content_type and hasattr(scraper, 'get_scraper_type') and 'html' in scraper.get_scraper_type():
                                logger.warning(f"Skipping HTML scraper {scraper.get_scraper_type()} for audio content from {fetcher.url} (content-type: {content_type})")
                                continue
                        except Exception as head_error:
                            logger.debug(f"HEAD request failed for {fetcher.url}: {head_error}, proceeding with GET")

                        response = client.get(fetcher.url)
                        response.raise_for_status()
                        scrape_result = scraper.extract_data(response.text, config=fetcher)
            except Exception as scrape_error:
                logger.error(f"Error making HTTP request to {fetcher.url}: {scrape_error}")
                error_msg = f"HTTP request error for {fetcher.url}: {str(scrape_error)}"

                # Mark fetcher as failed in state
                fetcher_states[str(fetcher.id)] = {
                    'fetcher_id': fetcher.id,
                    'category_slug': category_slug,
                    'priority': fetcher.priority,
                    'status': 'failed',
                    'error': error_msg,
                    'timestamp': task_start_time.isoformat(),
                    'task_id': task_id
                }

                errors.append(error_msg)
                if settings.DEBUG:
                    raise
                continue

            # Mark fetcher as successful and store data
            # Convert data to serializable format
            try:
                if hasattr(scrape_result, 'model_dump'):
                    data_dict = scrape_result.model_dump()
                elif hasattr(scrape_result, '__dict__'):
                    data_dict = scrape_result.__dict__.copy()
                else:
                    data_dict = str(scrape_result)

                # Convert any nested objects to serializable format
                data_dict = _make_json_serializable(data_dict)

            except Exception as serialize_error:
                logger.warning(f"Could not serialize scrape result for fetcher {fetcher.id}: {serialize_error}")
                data_dict = {"error": f"Serialization failed: {str(serialize_error)}"}

            fetcher_states[str(fetcher.id)] = {
                'fetcher_id': fetcher.id,
                'category_slug': category_slug,
                'priority': fetcher.priority,
                'status': 'completed',
                'data': data_dict,
                'timestamp': task_start_time.isoformat(),
                'task_id': task_id
            }

            scraped_count += 1
            logger.info(f"Successfully scraped fetcher {fetcher.id} for station {station.id}")

            # Check if we have complete song data (both name and artist)
            if (data_dict and 'current_song' in data_dict and data_dict['current_song'] and
                data_dict['current_song'].get('name') and data_dict['current_song'].get('artist')):
                logger.info(f"Found complete song data, stopping after first successful fetch for station {station.id}")

                # Create final merged data with just this successful fetch
                final_merged_data = _merge_fetcher_states_by_priority(fetcher_states, current_data, task_start_time)

                # Save final merged data
                final_success = False
                if final_merged_data:
                    final_merged_data.raw_data = fetcher_states
                    has_dirty_metadata = fetcher.dirty_metadata
                    final_success = StationService.upsert_station_now_playing(station.id, final_merged_data, dirty_metadata=has_dirty_metadata)

                return {
                    "success": final_success or scraped_count > 0,
                    "station_id": station.id,
                    "scraped_count": scraped_count,
                    "errors": errors,
                    "task_id": task_id,
                    "fetcher_states": fetcher_states,
                    "early_return": True
                }

        except Exception as error:
            logger.error(f"Error scraping {fetcher.url}: {error}")
            error_msg = f"Error scraping {fetcher.url}: {str(error)}"

            # Mark fetcher as failed in state
            fetcher_states[str(fetcher.id)] = {
                'fetcher_id': fetcher.id,
                'category_slug': fetcher.station_metadata_fetch_category.slug,
                'priority': fetcher.priority,
                'status': 'failed',
                'error': error_msg,
                'timestamp': task_start_time.isoformat(),
                'task_id': task_id
            }

            errors.append(error_msg)
            if settings.DEBUG:
                raise  # Re-raise the exception in debug mode for better debugging

    # Now merge data from all valid fetcher states
    final_merged_data = _merge_fetcher_states_by_priority(fetcher_states, current_data, task_start_time)

    # Save final merged data if available
    final_success = False
    if final_merged_data:
        # Update raw_data to include all fetcher states for this task
        final_merged_data.raw_data = fetcher_states

        # Determine if any successful fetcher has dirty_metadata=True
        has_dirty_metadata = False
        for fetcher in metadata_fetchers:
            fetcher_state = fetcher_states.get(str(fetcher.id))
            if fetcher_state and fetcher_state.get('status') == 'completed' and fetcher.dirty_metadata:
                has_dirty_metadata = True
                break

        final_success = StationService.upsert_station_now_playing(station.id, final_merged_data, dirty_metadata=has_dirty_metadata)

        # Note: Station uptime monitoring is now handled by a separate scheduled task
        # that runs every 5 minutes and performs proper HTTP requests to check stream availability

    return {
        "success": final_success or scraped_count > 0,
        "station_id": station.id,
        "scraped_count": scraped_count,
        "errors": errors,
        "task_id": task_id,
        "fetcher_states": fetcher_states
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
        with httpx.Client(timeout=60, verify=False, headers=headers, follow_redirects=True) as client:
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


def _reconstruct_station_data(data_dict):
    """Reconstruct StationNowPlayingData from dictionary"""
    from ..utils.data_types import StationNowPlayingData, SongData

    try:
        # Reconstruct current_song if present
        current_song = None
        if 'current_song' in data_dict and data_dict['current_song']:
            song_data = data_dict['current_song']
            if isinstance(song_data, dict):
                current_song = SongData(
                    name=song_data.get('name', ''),
                    artist=song_data.get('artist', '')
                )
            elif hasattr(song_data, 'name'):  # Already a SongData object
                current_song = song_data

        # Create StationNowPlayingData
        station_data = StationNowPlayingData(
            timestamp=data_dict.get('timestamp', timezone.now().isoformat()),
            current_song=current_song,
            listeners=data_dict.get('listeners'),
            raw_data=data_dict.get('raw_data', []),
            error=data_dict.get('error', [])
        )

        return station_data

    except Exception as e:
        logger.warning(f"Could not reconstruct station data: {e}")
        return None


def _make_json_serializable(obj):
    """Convert objects to JSON serializable format"""
    import json
    from datetime import datetime, date

    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif hasattr(obj, 'model_dump'):
        # Pydantic objects
        return _make_json_serializable(obj.model_dump())
    elif hasattr(obj, '__dict__'):
        # Regular objects
        return _make_json_serializable(obj.__dict__)
    else:
        # Fallback to string representation
        return str(obj)


def _merge_fetcher_states_by_priority(fetcher_states, current_data, task_start_time):
    """Merge data from fetcher states based on priority, considering only recent states"""
    from ..utils.data_types import StationNowPlayingData

    if not fetcher_states:
        return None

    # First, merge with existing valid states from current_data if it exists
    all_states = {}

    if current_data and current_data.raw_data:
        # Handle backward compatibility - raw_data might be a list or dict
        if isinstance(current_data.raw_data, dict):
            # New format: dictionary of fetcher states
            for fetcher_id, state in current_data.raw_data.items():
                if isinstance(state, dict) and 'timestamp' in state:
                    try:
                        state_time = parse(state['timestamp'])
                        if state_time >= task_start_time:
                            all_states[fetcher_id] = state
                    except (ValueError, TypeError):
                        # Skip invalid timestamps
                        continue
        # If it's a list (old format), we ignore it and start fresh

    # Add our new fetcher states
    all_states.update(fetcher_states)

    # Get completed states sorted by priority (lower order = higher priority)
    completed_states = []
    for fetcher_id, state in all_states.items():
        if state.get('status') == 'completed' and 'data' in state:
            completed_states.append((state['priority'], state['data'], state))

    if not completed_states:
        return None

    # Sort by priority (higher number = higher priority)
    completed_states.sort(key=lambda x: x[0], reverse=True)

    # Start with the highest priority data
    base_data_dict = completed_states[0][1]

    try:
        # Reconstruct the data properly
        merged_data = _reconstruct_station_data(base_data_dict)
        if not merged_data:
            logger.warning("Could not reconstruct StationNowPlayingData from base data")
            return None
    except Exception as e:
        logger.warning(f"Could not reconstruct StationNowPlayingData: {e}")
        return None

    # Merge additional data from lower priority states
    for priority, data_dict, state in completed_states[1:]:
        try:
            new_data = _reconstruct_station_data(data_dict)
            if new_data:
                merged_data = _merge_station_data_simple(merged_data, new_data)
        except Exception:
            logger.warning(f"Could not merge data from priority {priority}")
            continue

    return merged_data


def _merge_station_data_simple(base_data, new_data):
    """Simple merge of two StationNowPlayingData objects, preserving higher priority data"""
    # Merge raw_data arrays (keep both for debugging)
    if hasattr(new_data, 'raw_data') and new_data.raw_data:
        if not hasattr(base_data, 'raw_data') or not base_data.raw_data:
            base_data.raw_data = []
        base_data.raw_data.extend(new_data.raw_data)

    # Merge error arrays
    if hasattr(new_data, 'error') and new_data.error:
        if not hasattr(base_data, 'error') or not base_data.error:
            base_data.error = []
        base_data.error.extend(new_data.error)

    # NEVER override fields from higher priority data (base_data has highest priority)
    # Only fill in missing fields that higher priority source doesn't have

    # Only fill current_song if base doesn't have it or has incomplete data
    if (hasattr(new_data, 'current_song') and new_data.current_song and
        (not hasattr(base_data, 'current_song') or not base_data.current_song)):
        base_data.current_song = new_data.current_song
    elif (hasattr(base_data, 'current_song') and base_data.current_song and
          hasattr(new_data, 'current_song') and new_data.current_song):
        # Fill in missing artist/name from lower priority if higher priority is missing them
        if (not hasattr(base_data.current_song, 'artist') or not base_data.current_song.artist) and \
           (hasattr(new_data.current_song, 'artist') and new_data.current_song.artist):
            base_data.current_song.artist = new_data.current_song.artist

        if (not hasattr(base_data.current_song, 'name') or not base_data.current_song.name) and \
           (hasattr(new_data.current_song, 'name') and new_data.current_song.name):
            base_data.current_song.name = new_data.current_song.name

    # Only fill listeners if base doesn't have it
    if (hasattr(new_data, 'listeners') and new_data.listeners is not None and
        (not hasattr(base_data, 'listeners') or base_data.listeners is None)):
        base_data.listeners = new_data.listeners

    # Update timestamp to latest
    if hasattr(new_data, 'timestamp'):
        base_data.timestamp = new_data.timestamp

    return base_data


# NOTE: Station uptime monitoring has been moved to a dedicated uptime scraper
# using ffmpeg-python for more reliable stream checking. See:
# - scrapers/uptime.py
# - tasks/uptime_tasks.py
