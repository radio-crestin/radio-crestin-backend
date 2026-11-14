"""Public GraphQL lists are bounded whatever the caller asks for."""

import json

from django.test import TestCase, override_settings

from ..graphql.queries import MAX_PAGE_SIZE
from ..models import Artists, Songs

DUMMY_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}


@override_settings(CACHES=DUMMY_CACHE)
class GraphQLTestCase(TestCase):
    def graphql(self, query, **headers):
        response = self.client.post('/graphql', json.dumps({'query': query}),
                                    content_type='application/json', **headers)
        if response.status_code == 302:  # queries are redirected to GET for the CDN
            response = self.client.get(response['Location'], **headers)
        return response.json()


class PageSizeTests(GraphQLTestCase):
    @classmethod
    def setUpTestData(cls):
        artist = Artists.objects.create(name='Artist')
        Songs.objects.bulk_create(Songs(name=f'Song {n}', artist=artist) for n in range(MAX_PAGE_SIZE + 5))

    def test_a_list_without_limit_returns_one_page(self):
        data = self.graphql('{ songs { id } }')['data']
        self.assertEqual(len(data['songs']), MAX_PAGE_SIZE)

    def test_a_limit_above_the_page_size_is_capped(self):
        data = self.graphql('{ songs(limit: 100000) { id } }')['data']
        self.assertEqual(len(data['songs']), MAX_PAGE_SIZE)

    def test_offset_and_small_limits_still_work(self):
        data = self.graphql('{ songs(limit: 3, offset: 102) { id } }')['data']
        self.assertEqual(len(data['songs']), 3)

    def test_negative_values_return_an_empty_page_not_an_error(self):
        result = self.graphql('{ songs(limit: -1, offset: -5) { id } }')
        self.assertNotIn('errors', result)
        self.assertEqual(result['data']['songs'], [])

    def test_search_and_autocomplete_limits_are_capped(self):
        result = self.graphql('{ artists(search: "Art", limit: 5000) { id } autocomplete(query: "Song", limit: 5000) }')
        self.assertNotIn('errors', result)
        self.assertLessEqual(len(result['data']['autocomplete']), MAX_PAGE_SIZE)


class DocumentLimitTests(GraphQLTestCase):
    def test_many_aliases_are_rejected_before_running(self):
        from superapp.apps.graphql.schema import MAX_QUERY_ALIASES
        fields = ' '.join(f'a{n}: songs(limit: 100) {{ id }}' for n in range(MAX_QUERY_ALIASES + 1))
        result = self.graphql(f'{{ {fields} }}')
        self.assertIsNone(result.get('data'))
        self.assertIn('aliases', result['errors'][0]['message'])

    def test_an_oversized_document_is_rejected(self):
        from superapp.apps.graphql.schema import MAX_QUERY_TOKENS
        fields = ' '.join(['id'] * MAX_QUERY_TOKENS)
        result = self.graphql(f'{{ songs {{ {fields} }} }}')
        self.assertIsNone(result.get('data'))
        self.assertIn('token', result['errors'][0]['message'].lower())

    def test_the_apps_queries_and_introspection_still_run(self):
        from graphql import get_introspection_query
        from ..constants import STATIONS_GRAPHQL_QUERY
        self.assertNotIn('errors', self.graphql(STATIONS_GRAPHQL_QUERY))
        self.assertNotIn('errors', self.graphql(get_introspection_query()))


class PrivateStationRowsTests(GraphQLTestCase):
    """Posts and reviews of a private (or disabled) station stay with it."""

    @classmethod
    def setUpTestData(cls):
        from django.utils import timezone
        from ..models import Posts, Reviews
        from .helpers import make_station
        for slug, extra in (('open', {}), ('private', {'is_public': False}), ('off', {'disabled': True})):
            station = make_station(slug, **extra)
            post = Posts.objects.create(station=station, title=f'{slug} post', link='https://example.com',
                                        published=timezone.now())
            Reviews.objects.create(station=station, ip_address='203.0.113.1', stars=5, message=f'{slug} review')
            setattr(cls, f'{slug}_station', station)
            setattr(cls, f'{slug}_post', post)

    def test_lists_show_only_public_stations_rows(self):
        data = self.graphql('{ posts { title } reviews { message } }')['data']
        self.assertEqual([p['title'] for p in data['posts']], ['open post'])
        self.assertEqual([r['message'] for r in data['reviews']], ['open review'])

    def test_lookups_by_id_or_slug_do_not_reach_private_rows(self):
        data = self.graphql(f'{{ posts_by_pk(id: {self.private_post.id}) {{ title }} '
                            f'reviews(station_id: {self.private_station.id}) {{ message }} }}')['data']
        self.assertIsNone(data['posts_by_pk'])
        self.assertEqual(data['reviews'], [])
        self.assertEqual(self.graphql('{ reviews(station_slug: "private") { message } }')['data']['reviews'], [])


class ErrorDetailTests(GraphQLTestCase):
    """Unexpected exceptions reach the logs, not the caller."""

    def test_a_database_error_is_masked(self):
        from unittest.mock import patch
        from django.db import OperationalError
        error = OperationalError('could not connect to server at "10.20.20.5", port 5432')
        with patch('superapp.apps.radio_crestin.graphql.queries.Stations.objects.filter', side_effect=error):
            result = self.graphql('{ stations_metadata_history(station_slug: "x") { count } }')
            rest = self.client.get('/api/v1/stations-metadata-history', {'station_slug': 'x'}).json()
        for body in (result, rest):
            self.assertEqual([e['message'] for e in body['errors']], ['Internal server error'])
            self.assertNotIn('10.20.20.5', json.dumps(body))

    def test_messages_meant_for_callers_are_kept(self):
        result = self.graphql('{ stations_metadata_history(station_slug: "nope") { count } }')
        self.assertEqual(result['errors'][0]['message'], "Station 'nope' not found.")
