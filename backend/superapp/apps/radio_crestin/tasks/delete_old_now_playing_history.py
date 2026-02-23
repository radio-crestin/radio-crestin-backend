"""
Task to delete old StationsNowPlayingHistory records beyond retention period.
"""
import logging
import os
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from ..models import StationsNowPlayingHistory

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='priority',
)
def delete_old_now_playing_history(self):
    """
    Delete StationsNowPlayingHistory records older than the configured retention period.

    Retention is controlled by NOW_PLAYING_HISTORY_RETENTION_DAYS env var (default: 7).
    """
    try:
        retention_days = int(os.getenv('NOW_PLAYING_HISTORY_RETENTION_DAYS', '7'))
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        with transaction.atomic():
            old_records = StationsNowPlayingHistory.objects.filter(
                timestamp__lt=cutoff_date
            )
            old_count = old_records.count()

            if old_count == 0:
                logger.info("No old now playing history records to delete")
                return {
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No old records found',
                }

            deleted_count, _ = old_records.delete()
            logger.info(
                f"Deleted {deleted_count} now playing history records older than {retention_days} days"
            )

            return {
                'success': True,
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'message': f'Successfully deleted {deleted_count} old history records',
            }

    except Exception as e:
        logger.error(f"Error deleting old now playing history: {e}")
        return {
            'success': False,
            'error': str(e),
            'deleted_count': 0,
            'message': f'Failed to delete old history records: {e}',
        }
