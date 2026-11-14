"""trigger_metadata_fetch queues the station's scrape, for superusers only."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .helpers import make_station

TASK = 'superapp.apps.radio_crestin_scraping.tasks.scrape_station_metadata.scrape_station_metadata.delay'
TRIGGER = '''mutation($id: Int!) { trigger_metadata_fetch(station_id: $id) {
  ... on TriggerMetadataFetchResponse { success message }
  ... on OperationInfo { messages { message } } } }'''


class TriggerMetadataFetchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('trigger-me')
        cls.admin = get_user_model().objects.create_superuser(email='admin@example.com', password='x')

    def post(self, station_id):
        return self.client.post('/graphql', json.dumps({'query': TRIGGER, 'variables': {'id': station_id}}),
                                content_type='application/json').json()

    def trigger(self, station_id):
        return self.post(station_id)['data']['trigger_metadata_fetch']

    @patch(TASK)
    def test_superuser_queues_the_scrape(self, delay):
        self.client.force_login(self.admin)
        result = self.trigger(self.station.id)
        self.assertEqual(result, {'success': True,
                                  'message': 'Metadata fetch task scheduled for station trigger-me'})
        delay.assert_called_once_with(self.station.id)

    @patch(TASK)
    def test_unknown_station_queues_nothing(self, delay):
        self.client.force_login(self.admin)
        self.assertFalse(self.trigger(999999)['success'])
        delay.assert_not_called()

    @patch(TASK)
    def test_anonymous_caller_is_refused(self, delay):
        response = self.post(self.station.id)
        self.assertIsNone(response['data'])
        self.assertTrue(response['errors'])
        delay.assert_not_called()
