"""Rebuilds radiocrestin.ro when something it renders at build time changes.

The website renders stations, groups and the announcement card into its HTML at
build time, so a change triggers its Cloudflare Pages deploy hook (env
WEB_DEPLOY_HOOK_URL). Builds are coalesced:

- the first change schedules a build DEBOUNCE_SECONDS later; changes until then ride along;
- builds start at most once per MIN_INTERVAL_SECONDS: a change during that window
  schedules exactly one trailing build for when it ends.

The hook URL is a secret: it is never logged or returned.
"""
import logging
import os
import time

from django.core.cache import cache
from django.db import transaction

from .announcement_targeting import WEB_PLATFORMS

logger = logging.getLogger(__name__)

HOOK_URL_ENV = 'WEB_DEPLOY_HOOK_URL'
DEBOUNCE_SECONDS = 120
MIN_INTERVAL_SECONDS = 600
PENDING_KEY = 'website-rebuild:pending'      # a build is scheduled
LAST_BUILD_KEY = 'website-rebuild:last-build'  # when the hook was last called
PENDING_TTL = MIN_INTERVAL_SECONDS + DEBOUNCE_SECONDS + 300  # outlives the longest countdown


def hook_url() -> str:
    return os.environ.get(HOOK_URL_ENV, '').strip()


def is_web_visible(status: str, platforms) -> bool:
    """An announcement the website shows: active and not limited to the apps."""
    return status == 'active' and (not platforms or any(platform in WEB_PLATFORMS for platform in platforms))


def seconds_until_allowed(now: float = None) -> float:
    """How long until the next build may start (0 when it may start now)."""
    last_build = cache.get(LAST_BUILD_KEY)
    if last_build is None:
        return 0
    return max(0.0, last_build + MIN_INTERVAL_SECONDS - (now or time.time()))


def mark_built(now: float = None):
    cache.set(LAST_BUILD_KEY, now or time.time(), MIN_INTERVAL_SECONDS)


def schedule() -> bool:
    """Queues one build unless one is already pending; True when this call queued it."""
    if not hook_url():
        logger.info('Website rebuild skipped: %s is not set', HOOK_URL_ENV)
        return False
    if not cache.add(PENDING_KEY, 1, PENDING_TTL):
        return False
    countdown = max(DEBOUNCE_SECONDS, seconds_until_allowed())
    from ..tasks.trigger_web_deploy import trigger_web_deploy
    transaction.on_commit(lambda: trigger_web_deploy.apply_async(countdown=countdown))
    return True
