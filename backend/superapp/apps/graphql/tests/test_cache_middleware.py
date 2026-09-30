import time

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from django.middleware.cache import UpdateCacheMiddleware

from superapp.apps.graphql.cache_middleware import BoundedUpdateCacheMiddleware

LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'bounded-page-cache-tests',
    }
}
THIRTY_DAYS = 2592000


def cache_miss(path, **params):
    """A request as FetchFromCacheMiddleware leaves it on a miss: marked for storing."""
    request = RequestFactory().get(path, params)
    request._cache_update_cache = True
    return request


def immutable_view(request):
    response = HttpResponse('stations')
    response['Cache-Control'] = f'public, max-age={THIRTY_DAYS}, immutable'
    return response


@override_settings(CACHES=LOCMEM_CACHE, CACHE_MIDDLEWARE_SECONDS=0, CACHE_MIDDLEWARE_MAX_SECONDS=60)
class BoundedPageCacheTests(SimpleTestCase):
    """The site-wide page cache keeps a page in Redis at most CACHE_MIDDLEWARE_MAX_SECONDS."""

    def setUp(self):
        cache.clear()

    def test_redis_copy_is_capped_but_headers_keep_the_cdn_max_age(self):
        request = cache_miss('/api/v1/stations', timestamp='1790740000')
        response = BoundedUpdateCacheMiddleware(immutable_view)(request)

        self.assertIn(f'max-age={THIRTY_DAYS}', response['Cache-Control'])
        expiries = list(cache._expire_info.values())
        self.assertEqual(len(expiries), 2)  # page + its header list
        for expiry in expiries:
            self.assertLessEqual(expiry - time.time(), 60)

    def test_stock_middleware_keeps_the_page_for_thirty_days(self):
        """The bug this module fixes: without the cap Redis keeps every window a month."""
        UpdateCacheMiddleware(immutable_view)(cache_miss('/api/v1/stations', timestamp='1790740000'))
        self.assertGreater(max(cache._expire_info.values()) - time.time(), THIRTY_DAYS - 60)

    def test_response_without_max_age_is_not_cached(self):
        request = cache_miss('/api/v1/stations')
        BoundedUpdateCacheMiddleware(lambda r: HttpResponse('x'))(request)
        self.assertEqual(cache._expire_info, {})
