"""
Task to delete anonymous AppUsers older than 7 days.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import AppUsers

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='priority',
)
def delete_old_anonymous_users(self):
    """
    Delete anonymous AppUsers that are older than 7 days.

    This task removes old anonymous user records that are no longer needed,
    while preserving real users (those with email addresses). Only removes
    anonymous users that have an anonymous_id and no email.

    Returns:
        dict: Summary of cleanup results
    """
    try:
        with transaction.atomic():
            # Calculate cutoff date (7 days ago)
            cutoff_date = timezone.now() - timedelta(days=7)

            # Find old anonymous users (those without email and with anonymous_id)
            old_anonymous_users = AppUsers.objects.filter(
                created_at__lt=cutoff_date,
                email__isnull=True,  # No email means anonymous
                anonymous_id__isnull=False  # Has anonymous_id
            ).exclude(
                email=""  # Also exclude empty string emails
            )

            old_count = old_anonymous_users.count()

            if old_count == 0:
                logger.info("No old anonymous users to delete")
                return {
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No old anonymous users found'
                }

            # Delete old anonymous users
            deleted_count, deletion_details = old_anonymous_users.delete()

            logger.info(f"Deleted {deleted_count} anonymous users older than 7 days")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'message': f'Successfully deleted {deleted_count} old anonymous users'
            }

    except Exception as e:
        logger.error(f"Error deleting old anonymous users: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_count': 0,
            'message': f'Failed to delete old anonymous users: {e}'
        }
