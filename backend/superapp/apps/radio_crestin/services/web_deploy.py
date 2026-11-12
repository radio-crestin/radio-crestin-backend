"""Rebuilds radiocrestin.ro when an announcement it shows changes.

The website renders the announcement card into its HTML at build time, so a
change triggers its Cloudflare Pages deploy hook (env WEB_DEPLOY_HOOK_URL).
Changes are debounced: the first one schedules a build DEBOUNCE_SECONDS later,
and the ones in between ride along.
"""
import logging
import os

from django.core.cache import cache
from django.db import transaction

from .announcement_targeting import WEB_PLATFORMS

logger = logging.getLogger(__name__)

HOOK_URL_ENV = 'WEB_DEPLOY_HOOK_URL'
DEBOUNCE_SECONDS = 120
PENDING_KEY = 'announcements:web-deploy-pending'


def hook_url() -> str:
    return os.environ.get(HOOK_URL_ENV, '').strip()


def is_web_visible(status: str, platforms) -> bool:
    """Active and not limited to the apps."""
    return status == 'active' and (not platforms or any(platform in WEB_PLATFORMS for platform in platforms))


def schedule() -> bool:
    """Queues one build in DEBOUNCE_SECONDS unless one is already pending; True when queued."""
    if not hook_url():
        logger.info('Website rebuild skipped: %s is not set', HOOK_URL_ENV)
        return False
    if not cache.add(PENDING_KEY, 1, DEBOUNCE_SECONDS * 2):
        return False
    from ..tasks.trigger_web_deploy import trigger_web_deploy
    transaction.on_commit(lambda: trigger_web_deploy.apply_async(countdown=DEBOUNCE_SECONDS))
    return True
