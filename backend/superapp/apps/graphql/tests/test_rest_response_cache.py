import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings

from superapp.apps.graphql.rest_api import HttpMethod, RestApiEndpoint
from superapp.apps.graphql.rest_handler import GraphQLRestApiView

LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rest-response-cache-tests',
    }
}


def build_view(**overrides):
    """A view over a throwaway endpoint config, defaulting to caching enabled."""
    config_kwargs = {
        'path': 'api/v1/things',
        'graphql_query': 'query { things }',
        'method': HttpMethod.GET,
        'cache_ttl': 10,
    }
    config_kwargs.update(overrides)

    class ConfiguredView(GraphQLRestApiView):
        endpoint_config = RestApiEndpoint(**config_kwargs)

    return ConfiguredView()


@override_settings(CACHES=LOCMEM_CACHE)
class RestResponseCacheTests(SimpleTestCase):
    """The Redis-backed response cache on GraphQL-backed REST endpoints."""

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def call(self, view, path='/api/v1/things', **params):
        return view._handle_request(self.factory.get(path, params))

    def test_identical_requests_execute_graphql_once(self):
        view = build_view()
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': [1]}}
        ) as execute:
            first = self.call(view, timestamp='100')
            second = self.call(view, timestamp='100')

        self.assertEqual(execute.call_count, 1)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(json.loads(second.content), {'data': {'things': [1]}})

    def test_query_parameter_order_hits_the_same_entry(self):
        view = build_view()
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ) as execute:
            view._handle_request(
                self.factory.get('/api/v1/things?timestamp=100&station_slugs=a')
            )
            view._handle_request(
                self.factory.get('/api/v1/things?station_slugs=a&timestamp=100')
            )

        self.assertEqual(execute.call_count, 1)

    def test_different_parameters_are_cached_separately(self):
        view = build_view()
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ) as execute:
            self.call(view, timestamp='100')
            self.call(view, timestamp='110')

        self.assertEqual(execute.call_count, 2)

    def test_cache_ttl_zero_disables_caching(self):
        view = build_view(cache_ttl=0)
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ) as execute:
            self.call(view, timestamp='100')
            self.call(view, timestamp='100')

        self.assertEqual(execute.call_count, 2)

    def test_authorized_requests_bypass_the_shared_entry(self):
        view = build_view()
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ) as execute:
            view._handle_request(
                self.factory.get('/api/v1/things?timestamp=100', HTTP_AUTHORIZATION='Bearer x')
            )
            view._handle_request(
                self.factory.get('/api/v1/things?timestamp=100', HTTP_AUTHORIZATION='Bearer x')
            )

        self.assertEqual(execute.call_count, 2)

    def test_errors_are_not_cached(self):
        view = build_view()
        failing = {'data': None, 'errors': [{'message': 'boom'}]}
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value=failing
        ) as execute:
            self.call(view, timestamp='100')
            self.call(view, timestamp='100')

        self.assertEqual(execute.call_count, 2)

    def test_cache_control_headers_are_applied_to_cached_responses(self):
        view = build_view(cache_control='public, max-age=60')
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ):
            self.call(view, timestamp='100')
            cached = self.call(view, timestamp='100')

        self.assertEqual(cached['Cache-Control'], 'public, max-age=60')

    def test_post_endpoints_are_never_cached(self):
        view = build_view(method=HttpMethod.POST)
        with patch.object(
            GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}
        ) as execute:
            view._handle_request(self.factory.post('/api/v1/things', {'a': '1'}))
            view._handle_request(self.factory.post('/api/v1/things', {'a': '1'}))

        self.assertEqual(execute.call_count, 2)
