"""Brings the announcements' hourly and daily history up to date (every 5 minutes, on the normal queue)."""
import logging

from celery import shared_task

from ..services import announcement_stat_buckets

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, time_limit=30 * 60)
def update_announcement_stat_buckets():
    result = announcement_stat_buckets.upsert_recent()
    if result['buckets']:
        logger.info('Announcement history: %s buckets updated', result['buckets'])
    return result
