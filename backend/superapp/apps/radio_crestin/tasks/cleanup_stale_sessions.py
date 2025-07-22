"""
Cleanup task for managing stale and inactive listening sessions.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import ListeningSessions

logger = logging.getLogger(__name__)


@shared_task
def delete_inactive_listening_sessions():
    """
    Delete all inactive listening sessions to keep the database clean.
    
    This task removes sessions that have been marked as inactive, keeping only
    active sessions in the database. This provides a clean, efficient database
    with only relevant current session data.
    
    Returns:
        dict: Summary of cleanup results
    """
    try:
        with transaction.atomic():
            # Count inactive sessions before deletion
            inactive_sessions = ListeningSessions.objects.filter(is_active=False)
            inactive_count = inactive_sessions.count()
            
            if inactive_count == 0:
                logger.debug("No inactive sessions to delete")
                return {
                    'success': True,
                    'deleted_sessions': 0,
                    'message': 'No inactive sessions found'
                }
            
            # Delete all inactive sessions
            deleted_count, deletion_details = inactive_sessions.delete()
            
            logger.info(f"Deleted {deleted_count} inactive listening sessions")
            
            return {
                'success': True,
                'deleted_sessions': deleted_count,
                'message': f'Successfully deleted {deleted_count} inactive sessions'
            }
        
    except Exception as e:
        logger.error(f"Error deleting inactive sessions: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_sessions': 0,
            'message': f'Failed to delete inactive sessions: {e}'
        }


@shared_task
def mark_stale_sessions_inactive_and_delete():
    """
    Mark listening sessions as inactive if no activity in 60 seconds, then delete them.
    
    This task runs every 5 minutes to:
    1. Mark sessions as inactive if no activity for 60+ seconds
    2. Immediately delete those inactive sessions to keep database clean
    
    Returns:
        dict: Summary of session status updates and deletions
    """
    try:
        with transaction.atomic():
            # Step 1: Mark stale sessions as inactive
            cutoff_time = timezone.now() - timedelta(seconds=60)
            
            stale_sessions = ListeningSessions.objects.filter(
                is_active=True,
                last_activity__lt=cutoff_time
            )
            
            stale_count = stale_sessions.count()
            
            if stale_count == 0:
                logger.debug("No stale sessions found")
                return {
                    'success': True,
                    'marked_inactive': 0,
                    'deleted_sessions': 0,
                    'message': 'No stale sessions found'
                }
            
            # Mark as inactive and set end_time
            updated_count = stale_sessions.update(
                is_active=False,
                end_time=timezone.now()
            )
            
            # Step 2: Immediately delete the now-inactive sessions
            deleted_count, deletion_details = ListeningSessions.objects.filter(
                is_active=False
            ).delete()
            
            logger.info(
                f"Marked {updated_count} stale sessions as inactive and deleted "
                f"{deleted_count} inactive sessions (no activity for 60+ seconds)"
            )
            
            return {
                'success': True,
                'marked_inactive': updated_count,
                'deleted_sessions': deleted_count,
                'cutoff_time': cutoff_time.isoformat(),
                'message': f'Marked {updated_count} sessions inactive and deleted {deleted_count} sessions'
            }
        
    except Exception as e:
        logger.error(f"Error processing stale sessions: {e}")
        return {
            'success': False,
            'error': str(e),
            'marked_inactive': 0,
            'deleted_sessions': 0,
            'message': f'Failed to process stale sessions: {e}'
        }