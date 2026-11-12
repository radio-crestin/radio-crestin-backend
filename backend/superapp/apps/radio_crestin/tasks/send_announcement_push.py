"""Sends announcement push notifications: on demand from the admin, and at the start time."""
import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from ..models import Announcement, AnnouncementStatus, PushSchedule
from ..services import announcement_push

logger = logging.getLogger(__name__)


@shared_task(queue='priority')
def send_announcement_push(announcement_id: int):
    announcement = Announcement.objects.select_related('category').filter(pk=announcement_id).first()
    if announcement is None:
        return {'success': False, 'message': 'announcement not found'}
    return {'success': True, **announcement_push.send(announcement)}


def due_scheduled_pushes(now=None):
    """Confirmed "send at start time" notifications whose announcement has started and not ended."""
    now = now or timezone.now()
    return (
        Announcement.objects
        .filter(
            status=AnnouncementStatus.ACTIVE, push_enabled=True, push_schedule=PushSchedule.AT_START,
            push_confirmed_at__isnull=False, push_sent_at__isnull=True, starts_at__lte=now,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
    )


@shared_task(queue='priority')
def send_scheduled_announcement_pushes():
    """Every minute: queue each due notification once (claimed by stamping push_sent_at)."""
    if not announcement_push.is_configured():
        return {'success': True, 'queued': 0, 'message': 'push is not configured'}
    now = timezone.now()
    queued = 0
    for announcement_id in due_scheduled_pushes(now).values_list('id', flat=True):
        claimed = Announcement.objects.filter(pk=announcement_id, push_sent_at__isnull=True).update(push_sent_at=now)
        if claimed:
            send_announcement_push.delay(announcement_id)
            queued += 1
    if queued:
        logger.info('Queued %s scheduled announcement push(es)', queued)
    return {'success': True, 'queued': queued}
