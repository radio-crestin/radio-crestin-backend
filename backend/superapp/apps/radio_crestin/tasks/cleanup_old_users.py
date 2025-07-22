"""
Cleanup task for removing old anonymous AppUsers.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import AppUsers

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_app_users(days_old: int = 7):
    """
    Delete anonymous AppUsers older than the specified number of days.
    
    This task removes old anonymous user records that are no longer needed.
    It preserves real users (those with email addresses) and only removes
    anonymous users created for session tracking.
    
    Args:
        days_old: Number of days after which anonymous users should be deleted (default: 7)
        
    Returns:
        dict: Summary of cleanup results
    """
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    try:
        with transaction.atomic():
            # Only delete anonymous users (those without email and with anonymous_id)
            # Preserve real users even if they're old
            old_anonymous_users = AppUsers.objects.filter(
                created_at__lt=cutoff_date,
                email__isnull=True,  # No email means anonymous
                anonymous_id__isnull=False  # Has anonymous_id
            ).exclude(
                email=""  # Exclude empty string emails too
            )
            
            old_users_count = old_anonymous_users.count()
            
            if old_users_count == 0:
                logger.info("No old anonymous users to cleanup")
                return {
                    'success': True,
                    'deleted_users': 0,
                    'message': 'No old anonymous users found'
                }
            
            # Get some sample data for logging before deletion
            sample_users = list(old_anonymous_users.values('id', 'anonymous_id', 'created_at')[:5])
            
            # Bulk delete old anonymous users
            deleted_count, deletion_details = old_anonymous_users.delete()
            
            logger.info(
                f"Cleaned up {deleted_count} anonymous AppUsers older than {days_old} days "
                f"(cutoff: {cutoff_date}). Sample deleted users: {sample_users}"
            )
            
            return {
                'success': True,
                'deleted_users': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'days_old': days_old,
                'sample_deleted': sample_users,
                'message': f'Successfully deleted {deleted_count} old anonymous users'
            }
            
    except Exception as e:
        logger.error(f"Error cleaning up old anonymous users: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_users': 0,
            'message': f'Failed to cleanup anonymous users: {e}'
        }