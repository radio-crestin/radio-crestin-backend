"""
Task to delete stale listening sessions that haven't received signals in 60 seconds.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import ListeningSessions

logger = logging.getLogger(__name__)


@shared_task
def delete_stale_listening_sessions():
    """
    Delete listening sessions that haven't received any signal in the last 60 seconds.
    
    This task runs every minute to keep the database clean by removing sessions
    that are no longer active. Sessions are considered stale if they haven't
    had any activity (last_activity) in the last 60 seconds.
    
    Returns:
        dict: Summary of cleanup results
    """
    try:
        with transaction.atomic():
            # Calculate cutoff time (60 seconds ago)
            cutoff_time = timezone.now() - timedelta(seconds=60)
            
            # Find sessions with no activity in the last 60 seconds
            stale_sessions = ListeningSessions.objects.filter(
                last_activity__lt=cutoff_time
            )
            
            stale_count = stale_sessions.count()
            
            if stale_count == 0:
                logger.debug("No stale listening sessions to delete")
                return {
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No stale sessions found'
                }
            
            # Delete stale sessions
            deleted_count, deletion_details = stale_sessions.delete()
            
            logger.info(f"Deleted {deleted_count} stale listening sessions (no activity for 60+ seconds)")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'cutoff_time': cutoff_time.isoformat(),
                'message': f'Successfully deleted {deleted_count} stale listening sessions'
            }
        
    except Exception as e:
        logger.error(f"Error deleting stale listening sessions: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_count': 0,
            'message': f'Failed to delete stale sessions: {e}'
        }