import logging
from typing import Dict, Any
from celery import shared_task
from django.conf import settings

from ..scrapers.uptime import UptimeScraper

logger = logging.getLogger(__name__)


@shared_task(name='radio_crestin_scraping.check_station_uptime', time_limit=10)
def check_station_uptime(station_id: int = None) -> Dict[str, Any]:
    """Check uptime using ffmpeg for a single station or all stations"""
    logger.info(f"Starting ffmpeg uptime check for station: {station_id or 'all stations'}")

    scraper = UptimeScraper()

    try:
        # Run the appropriate check method (synchronous)
        if station_id:
            result = scraper.check_station_uptime(station_id)
        else:
            result = scraper.check_all_stations_uptime()

        logger.info(f"Completed ffmpeg uptime check: {result.get('success', False)}")
        return result

    except Exception as error:
        logger.error(f"Error during ffmpeg uptime check: {error}")
        if settings.DEBUG:
            raise
        return {"success": False, "error": str(error)}


@shared_task(name='radio_crestin_scraping.check_all_stations_uptime')
def check_all_stations_uptime() -> Dict[str, Any]:
    """Check uptime using ffmpeg for all active stations"""
    return check_station_uptime()
