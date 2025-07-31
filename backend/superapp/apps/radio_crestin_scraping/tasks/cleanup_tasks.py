import logging
from typing import Dict, Any
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ..services.station_service import StationService

logger = logging.getLogger(__name__)


@shared_task(name='radio_crestin_scraping.cleanup_old_scraped_data', time_limit=60)
def cleanup_old_scraped_data(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old station data.
    
    Args:
        days_to_keep: Number of days of data to keep
        
    Returns:
        Dict containing success status and days kept
    """
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
            raise
        return {"success": False, "error": str(error)}


@shared_task(name='radio_crestin_scraping.cleanup_old_dirty_metadata', time_limit=60)
def cleanup_old_dirty_metadata(days_to_keep: int = 7) -> Dict[str, Any]:
    """
    Clean up old songs and artists marked as dirty metadata.
    
    Args:
        days_to_keep: Number of days of dirty metadata to keep
        
    Returns:
        Dict containing success status and deletion counts
    """
    from superapp.apps.radio_crestin.models import Songs, Artists
    
    logger.info(f"Starting cleanup of dirty metadata older than {days_to_keep} days")
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Delete old dirty songs
        songs_deleted_count, _ = Songs.objects.filter(
            dirty_metadata=True,
            created_at__lt=cutoff_date
        ).delete()
        
        # Delete old dirty artists not referenced by any songs
        artists_deleted_count, _ = Artists.objects.filter(
            dirty_metadata=True,
            created_at__lt=cutoff_date,
            songs__isnull=True
        ).delete()
        
        logger.info(
            f"Deleted {songs_deleted_count} dirty songs and "
            f"{artists_deleted_count} dirty artists"
        )
        
        return {
            "success": True,
            "days_kept": days_to_keep,
            "songs_deleted": songs_deleted_count,
            "artists_deleted": artists_deleted_count
        }
        
    except Exception as error:
        logger.error(f"Error during dirty metadata cleanup: {error}")
        if settings.DEBUG:
            raise
        return {"success": False, "error": str(error)}