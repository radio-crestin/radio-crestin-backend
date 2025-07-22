"""
Cleanup task for removing old listening sessions.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import ListeningSessions

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_listening_sessions(days_old: int = 7):
    """
    Delete listening sessions older than the specified number of days.
    
    This task removes old session data to prevent database bloat while
    preserving recent analytics data. Runs efficiently with bulk deletion.
    
    Args:
        days_old: Number of days after which sessions should be deleted (default: 7)
        
    Returns:
        dict: Summary of cleanup results
    """
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    try:
        with transaction.atomic():
            # Count sessions before deletion
            old_sessions_count = ListeningSessions.objects.filter(
                created_at__lt=cutoff_date
            ).count()
            
            if old_sessions_count == 0:
                logger.info("No old listening sessions to cleanup")
                return {
                    'success': True,
                    'deleted_sessions': 0,
                    'message': 'No old listening sessions found'
                }
            
            # Bulk delete old sessions for efficiency
            # This will cascade delete related objects automatically
            deleted_count, deletion_details = ListeningSessions.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(
                f"Cleaned up {deleted_count} listening sessions older than {days_old} days "
                f"(cutoff: {cutoff_date})"
            )
            
            return {
                'success': True,
                'deleted_sessions': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'days_old': days_old,
                'message': f'Successfully deleted {deleted_count} old listening sessions'
            }
            
    except Exception as e:
        logger.error(f"Error cleaning up old listening sessions: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_sessions': 0,
            'message': f'Failed to cleanup listening sessions: {e}'
        }