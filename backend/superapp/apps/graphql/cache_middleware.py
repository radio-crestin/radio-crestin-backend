"""Site-wide page cache that never keeps a page in Redis longer than a ceiling.

Django's UpdateCacheMiddleware stores a response for its Cache-Control max-age.
The timestamped REST URLs (`?timestamp=<10s window>`) send
`max-age=2592000, immutable`, which is right for browsers and Cloudflare but
made Redis keep a new page every 10 seconds for 30 days (Redis grew until it
was OOM-killed). Here the Redis copy lives at most
CACHE_MIDDLEWARE_MAX_SECONDS; the response headers stay untouched.
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
    @property
    def cache(self):
        return CappedCache(super().cache, settings.CACHE_MIDDLEWARE_MAX_SECONDS)
