"""POSTs the website's deploy hook (scheduled by services/web_deploy.schedule).

The hook URL is a secret, and requests' exception messages contain it: logs and the
task result only ever say the error's type or the HTTP status.
"""
import logging

import requests
from celery import shared_task
from django.core.cache import cache

from ..services import web_deploy

logger = logging.getLogger(__name__)


@shared_task(queue='priority')
def trigger_web_deploy(force: bool = False):
    """Calls the hook; a scheduled run that lands inside the minimum interval waits for its end.

    force=True (the admin's "Rebuild website now") builds right away.
    """
    if not force:
        wait = web_deploy.seconds_until_allowed()
        if wait > 0:
            trigger_web_deploy.apply_async(countdown=wait)  # still pending: later changes ride along
            return {'success': True, 'message': 'waiting for the minimum interval'}
        # Changes from now on schedule the next (trailing) build.
        cache.delete(web_deploy.PENDING_KEY)

    url = web_deploy.hook_url()
    if not url:
        logger.info('Website rebuild skipped: %s is not set', web_deploy.HOOK_URL_ENV)
        return {'success': False, 'message': 'hook not configured'}

    web_deploy.mark_built()
    try:
        response = requests.post(url, timeout=15)
    except requests.RequestException as error:
        logger.error('Website deploy hook failed: %s', type(error).__name__)
        return {'success': False, 'message': 'request failed'}
    if not response.ok:
        logger.error('Website deploy hook failed: HTTP %s', response.status_code)
        return {'success': False, 'message': f'HTTP {response.status_code}'}
    logger.info('Website rebuild triggered')
    return {'success': True, 'status_code': response.status_code}
