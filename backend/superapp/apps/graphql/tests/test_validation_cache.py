from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from superapp.apps.graphql.schema import schema

LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'validation-cache-tests',
    }
}


@override_settings(CACHES=LOCMEM_CACHE)
class ValidationCacheTests(SimpleTestCase):
    """Validating a query never writes to the shared cache.

    strawberry-django's DjangoValidationCache keyed Redis entries on
    `<GraphQLSchema object at 0x…>`: an address differs per process, so every
    process wrote its own 7-day keys and none was ever read by another.
    """

    def setUp(self):
        cache.clear()

    def test_running_a_query_writes_no_cache_key(self):
        result = schema.execute_sync('query Q { __typename }')

        self.assertIsNone(result.errors)
        self.assertEqual(cache._cache, {})
