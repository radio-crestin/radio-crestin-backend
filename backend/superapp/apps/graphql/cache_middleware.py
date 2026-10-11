"""Site-wide page cache that never keeps a page in Redis longer than a ceiling.

Django's UpdateCacheMiddleware stores a response for its Cache-Control max-age.
The timestamped REST URLs (`?timestamp=<10s window>`) send
`max-age=2592000, immutable`, which is right for browsers and Cloudflare but
made Redis keep a new page every 10 seconds for 30 days (Redis grew until it
was OOM-killed). Here the Redis copy lives at most
CACHE_MIDDLEWARE_MAX_SECONDS; the response headers stay untouched.

A view sets `response._skip_page_cache` for an answer that may live in Redis
only briefly (the REST handler does it for a CachePolicy with
`page_cacheable=False`): the page cache keys on the URL alone, so it would
keep serving that answer for the full ceiling.
"""

from django.conf import settings
from django.middleware.cache import UpdateCacheMiddleware


class CappedCache:
    """Wraps a cache so set() never keeps a key longer than max_seconds."""

    def __init__(self, cache, max_seconds):
        self._cache = cache
        self._max_seconds = max_seconds

    def set(self, key, value, timeout, version=None):
        return self._cache.set(key, value, min(timeout, self._max_seconds), version=version)

    def __getattr__(self, name):
        return getattr(self._cache, name)


class BoundedUpdateCacheMiddleware(UpdateCacheMiddleware):
    def _should_update_cache(self, request, response):
        if getattr(response, '_skip_page_cache', False):
            return False
        return super()._should_update_cache(request, response)

    @property
    def cache(self):
        return CappedCache(super().cache, settings.CACHE_MIDDLEWARE_MAX_SECONDS)
