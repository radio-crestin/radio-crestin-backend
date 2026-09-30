"""A response computed for one caller must never be stored for another.

Shared caches (Cloudflare, Django's Redis page cache) key on the URL, not on
who asked, so anything a request with credentials receives must be private.
"""
import json
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from superapp.apps.graphql.graphql_get_view import GraphQLWithGetRedirectView
from superapp.apps.graphql.middleware import PublicCacheHeadersMiddleware
from superapp.apps.graphql.rest_api import HttpMethod, RestApiEndpoint
from superapp.apps.graphql.rest_handler import GraphQLRestApiView

LOCMEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'credentialed-caching-tests',
    }
}
PUBLIC_QUERY = 'query Q @cache_control(max_age: 30, public: true) { __typename }'


def public_view(request):
    response = HttpResponse('stations')
    response['Cache-Control'] = 'public, max-age=60'
    response['Vary'] = 'Accept-Encoding, Cookie'
    response.set_cookie('csrftoken', 'abc')
    response._public_cacheable = True
    return response


def with_session(request):
    request.COOKIES[settings.SESSION_COOKIE_NAME] = 'signed-session'
    return request


class PublicCacheHeadersMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PublicCacheHeadersMiddleware(public_view)

    def test_anonymous_response_stays_public_without_cookies(self):
        response = self.middleware(self.factory.get('/api/v1/stations'))
        self.assertEqual(response['Cache-Control'], 'public, max-age=60')
        self.assertEqual(response['Vary'], 'Accept-Encoding')
        self.assertFalse(response.has_header('Set-Cookie'))

    def test_session_cookie_makes_it_private(self):
        response = self.middleware(with_session(self.factory.get('/api/v1/stations')))
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_credential_headers_make_it_private(self):
        for header in ('HTTP_AUTHORIZATION', 'HTTP_X_STREAMING_API_KEY', 'HTTP_X_API_KEY'):
            with self.subTest(header=header):
                response = self.middleware(self.factory.get('/api/v1/stations', **{header: 'secret'}))
                self.assertEqual(response['Cache-Control'], 'private, no-store')


@override_settings(CACHES=LOCMEM_CACHE)
class RestHandlerCredentialTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

        class View(GraphQLRestApiView):
            endpoint_config = RestApiEndpoint(
                path='api/v1/things',
                graphql_query='query { things }',
                method=HttpMethod.GET,
                cache_control='public, max-age=2592000, immutable',
            )

        self.view = View()

    def get(self, request):
        with patch.object(GraphQLRestApiView, '_execute_graphql', return_value={'data': {'things': []}}):
            return self.view.dispatch(request)

    def test_anonymous_request_is_public(self):
        response = self.get(self.factory.get('/api/v1/things'))
        self.assertEqual(response['Cache-Control'], 'public, max-age=2592000, immutable')
        self.assertTrue(response._public_cacheable)

    def test_authorization_header_is_private(self):
        response = self.get(self.factory.get('/api/v1/things', HTTP_AUTHORIZATION='Token x'))
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertFalse(getattr(response, '_public_cacheable', False))

    def test_session_cookie_is_private(self):
        response = self.get(with_session(self.factory.get('/api/v1/things')))
        self.assertEqual(response['Cache-Control'], 'private, no-store')


@override_settings(CACHES=LOCMEM_CACHE)
class GraphQLGetCredentialTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.view = GraphQLWithGetRedirectView.as_view()

    def get(self, query, **extra):
        return self.view(self.factory.get('/graphql', {'query': query}, **extra))

    def test_anonymous_query_keeps_its_cache_directive(self):
        response = self.get(PUBLIC_QUERY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('public', response['Cache-Control'])

    def test_query_with_api_key_is_private(self):
        response = self.get(PUBLIC_QUERY, HTTP_AUTHORIZATION='Token x')
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_query_with_session_is_private(self):
        request = with_session(self.factory.get('/graphql', {'query': PUBLIC_QUERY}))
        response = self.view(request)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_mutation_over_get_is_refused(self):
        response = self.get('mutation { __typename }')
        self.assertEqual(response.status_code, 405)
        self.assertIn('POST', json.loads(response.content)['errors'][0]['message'])
