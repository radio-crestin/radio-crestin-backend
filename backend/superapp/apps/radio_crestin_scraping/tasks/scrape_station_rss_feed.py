import logging
from typing import Dict, Any
from celery import shared_task
from django.conf import settings
import httpx
import feedparser
from email.utils import parsedate_to_datetime

from ..services.station_service import StationService
from ..utils.data_types import StationRssFeedData, RssFeedPost

logger = logging.getLogger(__name__)


@shared_task(name='radio_crestin_scraping.scrape_station_rss_feed', time_limit=120)
def scrape_station_rss_feed(station_id: int) -> Dict[str, Any]:
    """
    Scrape RSS feed for a single station.
    
    Returns:
        Dict containing success status, posts count, and any errors
    """
    from superapp.apps.radio_crestin.models import Stations
    
    try:
        station = Stations.objects.get(id=station_id)
        
        if station.disabled:
            logger.info(f"Station {station_id} is disabled - skipping RSS")
            return {"success": True, "posts_count": 0, "station_disabled": True}
        
        if not station.rss_feed:
            logger.info(f"Station {station_id} has no RSS feed configured")
            return {"success": True, "posts_count": 0}
            
    except Stations.DoesNotExist:
        logger.error(f"Station {station_id} not found")
        return {"success": False, "error": f"Station {station_id} not found"}
    
    try:
        # Fetch RSS feed
        posts = _fetch_rss_posts(station.rss_feed)
        
        # Save posts
        rss_data = StationRssFeedData(posts=posts)
        success = StationService.upsert_station_posts(station_id, rss_data)
        
        return {
            "success": success,
            "station_id": station_id,
            "posts_count": len(posts)
        }
        
    except Exception as error:
        logger.error(f"Error scraping RSS for station {station_id}: {error}")
        if settings.DEBUG:
            raise
        return {
            "success": False,
            "station_id": station_id,
            "error": str(error)
        }


def _fetch_rss_posts(rss_url: str) -> list[RssFeedPost]:
    """
    Fetch and parse RSS feed posts.
    
    Args:
        rss_url: URL of the RSS feed
        
    Returns:
        List of parsed RSS posts
    """
    logger.info(f"Fetching RSS feed: {rss_url}")
    
    # Browser-like headers for better compatibility
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Fetch RSS content
    with httpx.Client(
        timeout=60, 
        verify=False, 
        headers=headers, 
        follow_redirects=True
    ) as client:
        response = client.get(rss_url)
        response.raise_for_status()
    
    # Parse RSS feed
    feed = feedparser.parse(response.text)
    posts = []
    
    for entry in feed.entries:
        # Parse published date
        published_iso = ''
        if hasattr(entry, 'published') and entry.published:
            try:
                parsed_date = parsedate_to_datetime(entry.published)
                published_iso = parsed_date.isoformat()
            except (ValueError, TypeError):
                published_iso = entry.published
        
        # Create post object
        post = RssFeedPost(
            title=getattr(entry, 'title', ''),
            description=getattr(entry, 'description', ''),
            link=getattr(entry, 'link', ''),
            published=published_iso
        )
        posts.append(post)
    
    return posts