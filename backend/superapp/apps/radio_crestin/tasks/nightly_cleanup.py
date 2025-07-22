"""
Nightly database cleanup orchestration task.
"""
import logging
from django.utils import timezone
from celery import shared_task

from .cleanup_old_sessions import cleanup_old_listening_sessions
from .cleanup_old_users import cleanup_old_app_users
from .cleanup_stale_sessions import delete_inactive_listening_sessions

logger = logging.getLogger(__name__)


@shared_task
def nightly_database_cleanup():
    """
    Combined nightly cleanup task that runs all cleanup operations.
    
    This is the main task that should be scheduled to run nightly.
    It orchestrates all cleanup operations and provides a comprehensive report.
    
    Returns:
        dict: Combined results from all cleanup operations
    """
    logger.info("Starting nightly database cleanup...")
    
    results = {
        'started_at': timezone.now().isoformat(),
        'tasks': {}
    }
    
    try:
        # Run delete_inactive_listening_sessions first (cleanup any existing inactive sessions)
        logger.info("Step 1: Deleting any existing inactive sessions...")
        inactive_result = delete_inactive_listening_sessions.delay().get()
        results['tasks']['delete_inactive_sessions'] = inactive_result
        
        # Clean up old listening sessions
        logger.info("Step 2: Cleaning up old listening sessions...")
        sessions_result = cleanup_old_listening_sessions.delay(days_old=7).get()
        results['tasks']['old_sessions'] = sessions_result
        
        # Clean up old anonymous users
        logger.info("Step 3: Cleaning up old anonymous users...")
        users_result = cleanup_old_app_users.delay(days_old=7).get()
        results['tasks']['old_users'] = users_result
        
        # Calculate totals
        total_sessions_deleted = sessions_result.get('deleted_sessions', 0)
        total_users_deleted = users_result.get('deleted_users', 0)
        total_inactive_deleted = inactive_result.get('deleted_sessions', 0)
        
        results['completed_at'] = timezone.now().isoformat()
        results['summary'] = {
            'total_sessions_deleted': total_sessions_deleted,
            'total_users_deleted': total_users_deleted,
            'total_inactive_sessions_deleted': total_inactive_deleted,
            'all_successful': all(
                task_result.get('success', False) 
                for task_result in results['tasks'].values()
            )
        }
        
        logger.info(
            f"Nightly cleanup completed: "
            f"{total_sessions_deleted} old sessions deleted, "
            f"{total_users_deleted} anonymous users deleted, "
            f"{total_inactive_deleted} inactive sessions deleted"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in nightly database cleanup: {e}")
        results['error'] = str(e)
        results['completed_at'] = timezone.now().isoformat()
        return results