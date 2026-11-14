"""Deletes raw announcement events past their retention; the totals stay on each announcement."""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ..models import AnnouncementEvent
from ..models.announcement_events import RETENTION_DAYS

logger = logging.getLogger(__name__)


@shared_task(queue='priority')
def delete_old_announcement_events():
    cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
    deleted_count, _ = AnnouncementEvent.objects.filter(created_at__lt=cutoff).delete()
    if deleted_count:
        logger.info('Deleted %s announcement events older than %s days', deleted_count, RETENTION_DAYS)
    return {'success': True, 'deleted_count': deleted_count, 'cutoff_date': cutoff.isoformat()}
