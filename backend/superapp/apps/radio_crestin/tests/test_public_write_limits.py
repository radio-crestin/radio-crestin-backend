"""Public writes have size limits and per-caller budgets."""

import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from ..models import AppUsers, Reviews
from .helpers import make_station

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'write-limits'}}
MUTATIONS = 'superapp.apps.radio_crestin.graphql.mutations'
DEVICES = 'superapp.apps.radio_crestin.views.device_registration_api'

REVIEW = '''mutation($input: SubmitReviewInput!) { submit_review(input: $input) {
  ... on SubmitReviewResponse { success message } } }'''
SHARE = '''mutation($id: String!) { get_share_link(anonymous_id: $id) {
  ... on GetShareLinkResponse { success message } } }'''


@override_settings(CACHES=LOCMEM)
class LimitTestCase(TestCase):
    def setUp(self):
        cache.clear()

    def mutate(self, query, variables, ip='203.0.113.7'):
        response = self.client.post('/graphql', json.dumps({'query': query, 'variables': variables}),
                                    content_type='application/json', HTTP_CF_CONNECTING_IP=ip)
        return next(iter(response.json()['data'].values()))


class ReviewLimitTests(LimitTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.station = make_station('reviewed')

    def review(self, ip='203.0.113.7', **fields):
        return self.mutate(REVIEW, {'input': {'station_slug': 'reviewed', 'stars': 5, **fields}}, ip=ip)

    def test_an_ip_over_its_budget_is_refused_and_others_are_not(self):
        with patch(f'{MUTATIONS}.REVIEW_RATE_PER_IP', '2/h'):
            self.assertTrue(self.review()['success'])
            self.assertTrue(self.review(message='changed my mind')['success'])
            self.assertFalse(self.review(message='third')['success'])
            self.assertTrue(self.review(ip='198.51.100.1')['success'])
        self.assertEqual(Reviews.objects.get(ip_address='203.0.113.7').message, 'changed my mind')

    def test_an_oversized_message_is_refused(self):
        result = self.review(message='x' * 2001)
        self.assertFalse(result['success'])
        self.assertFalse(Reviews.objects.exists())


class ShareLinkLimitTests(LimitTestCase):
    def test_an_oversized_id_is_refused_without_a_user(self):
        self.assertFalse(self.mutate(SHARE, {'id': 'x' * 513})['success'])
        self.assertFalse(AppUsers.objects.exists())

    def test_an_ip_over_its_budget_creates_nothing(self):
        with patch(f'{MUTATIONS}.SHARE_LINK_RATE_PER_IP', '1/h'):
            self.assertTrue(self.mutate(SHARE, {'id': 'device-1'})['success'])
            self.assertFalse(self.mutate(SHARE, {'id': 'device-2'})['success'])
        self.assertFalse(AppUsers.objects.filter(anonymous_id='device-2').exists())


class DeviceRegistrationLimitTests(LimitTestCase):
    def register(self, body):
        return self.client.post('/api/v1/devices/register/', json.dumps(body), content_type='application/json',
                                HTTP_CF_CONNECTING_IP='203.0.113.7')

    def test_an_oversized_payload_is_refused(self):
        response = self.register({'device_id': 'd1', 'junk': 'x' * 20000})
        self.assertEqual(response.status_code, 413)
        self.assertFalse(AppUsers.objects.exists())

    def test_an_oversized_device_id_or_token_is_refused(self):
        self.assertEqual(self.register({'device_id': 'd' * 513}).status_code, 400)
        self.assertEqual(self.register({'device_id': 'd1', 'fcm_token': 't' * 4097}).status_code, 400)

    def test_a_device_over_its_budget_is_refused(self):
        with patch(f'{DEVICES}.RATE_PER_DEVICE', '2/h'):
            statuses = [self.register({'device_id': 'd1'}).status_code for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])
