"""POSTs the website's deploy hook (scheduled by services/web_deploy.schedule)."""
import logging

import requests
from celery import shared_task
from django.core.cache import cache

from ..services import web_deploy

logger = logging.getLogger(__name__)


@shared_task(queue='priority')
def trigger_web_deploy():
    # Changes from now on schedule a new build.
    cache.delete(web_deploy.PENDING_KEY)
    url = web_deploy.hook_url()
    if not url:
        logger.info('Website rebuild skipped: %s is not set', web_deploy.HOOK_URL_ENV)
        return {'success': False, 'message': 'hook not configured'}
    try:
        response = requests.post(url, timeout=15)
    except requests.RequestException as error:
        logger.error('Website deploy hook failed: %s', error)
        return {'success': False, 'message': str(error)}
    if not response.ok:
        logger.error('Website deploy hook answered %s', response.status_code)
    return {'success': response.ok, 'status_code': response.status_code}
