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


