"""The client-written @cached directive cannot pin results in Redis."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from superapp.apps.graphql.graphql.extensions import MAX_DIRECTIVE_TTL
from superapp.apps.graphql.schema import schema

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'cached-directive'}}


@override_settings(CACHES=LOCMEM)
class CachedDirectiveTests(SimpleTestCase):
    def stored_ttl(self, directive):
        with patch('superapp.apps.graphql.graphql.extensions.cache.set') as cache_set:
            result = schema.execute_sync(f'query {directive} {{ current_time }}')
        self.assertIsNone(result.errors)
        return cache_set.call_args.args[2] if cache_set.called else None

    def test_a_long_ttl_is_capped(self):
        self.assertEqual(self.stored_ttl('@cached(ttl: 31536000)'), MAX_DIRECTIVE_TTL)

    def test_a_short_ttl_is_kept(self):
        self.assertEqual(self.stored_ttl('@cached(ttl: 5)'), 5)

    def test_zero_or_negative_ttl_stores_nothing(self):
        self.assertIsNone(self.stored_ttl('@cached(ttl: 0)'))
        self.assertIsNone(self.stored_ttl('@cached(ttl: -5)'))


@override_settings(CACHES=LOCMEM)
class RequestIsolationTests(SimpleTestCase):
    """One request's @cached must not answer or shape the next one.

    The extension instances outlive a request: the cache lookup ran before
    the next request parsed its own query, with the previous request's key,
    so `{ health }` was answered with another query's stored data (and the
    REST endpoints would have stored that answer for their URL)."""

    def test_the_next_query_gets_its_own_data(self):
        first = schema.execute_sync('query @cached(ttl: 30) { current_time }')
        second = schema.execute_sync('query { health }')
        self.assertEqual(second.data, {'health': True})
        again = schema.execute_sync('query @cached(ttl: 30) { current_time }')
        self.assertEqual(again.data, first.data)  # served from the cache

    def test_each_thread_has_its_own_extensions(self):
        import threading
        mine, theirs = schema._sync_extensions, []
        thread = threading.Thread(target=lambda: theirs.append(schema._sync_extensions))
        thread.start()
        thread.join()
        self.assertTrue(all(a is not b for a, b in zip(mine, theirs[0])))
        self.assertIs(schema._sync_extensions, mine)
