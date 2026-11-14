"""Emails the team about a new contact message (see services/contact_notify)."""
import logging

from celery import shared_task

from ..models import ContactMessage
from ..services import contact_notify

logger = logging.getLogger(__name__)


@shared_task
def notify_contact_message(message_id: int):
    message = ContactMessage.objects.filter(pk=message_id).first()
    if message is None:
        return {'success': False, 'message': 'not found'}
    try:
        sent = contact_notify.send(message)
    except Exception as error:
        logger.error('Contact notification for %s failed: %s', message_id, error)
        return {'success': False, 'message': str(error)}
    if not sent:
        logger.info('Contact notification skipped: %s is not set', contact_notify.RECIPIENTS_ENV)
    return {'success': sent}
