import json
import time
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import Announcement, AnnouncementEvent, AppUsers
from ..services.announcement_events import MAX_ANNOUNCEMENTS_PER_REQUEST, MAX_EVENTS_PER_REQUEST
from ..views import announcements_api
from ..views.announcements_api import EVENTS_RATE_PER_DEVICE, EVENTS_RATE_PER_IP

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EVENTS_URL = '/api/v1/announcements/events/'


def make_announcement(slug, **fields):
    defaults = {'title': slug, 'status': 'active', 'starts_at': timezone.now() - timedelta(hours=1)}
    defaults.update(fields)
    return Announcement.objects.create(slug=slug, **defaults)


def iso_ago(**delta):
    return (timezone.now() - timedelta(**delta)).isoformat().replace('+00:00', 'Z')


@override_settings(CACHES=LOCMEM_CACHE)
class EventsEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.announcement = make_announcement('concert')

    def post(self, body, content_type='text/plain;charset=UTF-8', **headers):
        return self.client.post(EVENTS_URL, json.dumps(body), content_type=content_type, **headers)

    def test_text_plain_beacon_is_accepted_and_counted(self):
        two_minutes_ago = iso_ago(minutes=2)
        response = self.post({
            'device_id': 'web-1', 'platform': 'web', 'locale': 'ro-RO',
            'events': [
                {'slug': 'concert', 'type': 'impression', 'position': 0, 'at': two_minutes_ago},
                {'slug': 'concert', 'type': 'clicked', 'position': 0, 'target': 'card',
                 'placement': 'station', 'station_slug': 'radio-elim'},
                {'slug': 'concert', 'type': 'dismissed'},
                {'slug': 'concert', 'type': 'page_viewed'},
                {'slug': 'concert', 'type': 'secondary_clicked'},
                {'slug': 'concert', 'type': 'push_opened'},
            ],
        }, HTTP_CF_IPCOUNTRY='DE', HTTP_CF_CONNECTING_IP='86.120.1.2')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'accepted': 6, 'country': 'DE'})
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

        self.announcement.refresh_from_db()
        self.assertEqual(
            (self.announcement.impressions, self.announcement.clicks, self.announcement.dismissals,
             self.announcement.page_views, self.announcement.secondary_clicks, self.announcement.push_opens),
            (1, 1, 1, 1, 1, 1),
        )
        click = AnnouncementEvent.objects.get(type='clicked')
        self.assertEqual((click.device_id, click.platform, click.locale, click.app_version), ('web-1', 'web', 'ro-RO', ''))
        self.assertEqual((click.country, click.ip, click.target, click.position), ('DE', '86.120.1.2', 'card', 0))
        self.assertEqual((click.placement, click.station_slug), ('station', 'radio-elim'))
        impression = AnnouncementEvent.objects.get(type='impression')
        self.assertEqual(impression.occurred_at.isoformat().replace('+00:00', 'Z'), two_minutes_ago)

    def test_json_content_type_also_works(self):
        response = self.post({'device_id': 'a', 'events': [{'slug': 'concert', 'type': 'clicked'}]},
                             content_type='application/json')
        self.assertEqual(response.json()['accepted'], 1)

    def test_unknown_slugs_types_and_targets_are_skipped(self):
        response = self.post({'device_id': 'a', 'events': [
            {'slug': 'nope', 'type': 'impression'},
            {'slug': 'concert', 'type': 'hacked'},
            {'slug': 'concert', 'type': 'clicked', 'target': 'everything', 'position': 'x'},
            'not an object',
        ]})
        self.assertEqual(response.json(), {'status': 'ok', 'accepted': 1, 'country': None})
        event = AnnouncementEvent.objects.get()
        self.assertEqual((event.target, event.position), ('', None))

    def test_at_most_100_events_are_read(self):
        filler = [{'slug': 'concert', 'type': 'not-a-type'}]
        click = {'slug': 'concert', 'type': 'clicked'}
        response = self.post({'device_id': 'a', 'events': filler * MAX_EVENTS_PER_REQUEST + [click]})
        self.assertEqual(response.json()['accepted'], 0)
        response = self.post({'device_id': 'a', 'events': filler * (MAX_EVENTS_PER_REQUEST - 1) + [click]})
        self.assertEqual(response.json()['accepted'], 1)

    def test_at_most_10_announcements_per_request(self):
        Announcement.objects.bulk_create([
            Announcement(slug=f'bulk-{index}', title='bulk', position=100 + index) for index in range(MAX_ANNOUNCEMENTS_PER_REQUEST + 2)
        ])
        events = [{'slug': f'bulk-{index}', 'type': 'impression'} for index in range(MAX_ANNOUNCEMENTS_PER_REQUEST + 2)]
        response = self.post({'device_id': 'a', 'events': events})
        self.assertEqual(response.json()['accepted'], MAX_ANNOUNCEMENTS_PER_REQUEST)
        self.assertEqual(
            set(Announcement.objects.filter(impressions=1).values_list('slug', flat=True)),
            {f'bulk-{index}' for index in range(MAX_ANNOUNCEMENTS_PER_REQUEST)},
        )

    def test_events_too_old_or_too_far_ahead_are_skipped(self):
        response = self.post({'device_id': 'a', 'events': [
            {'slug': 'concert', 'type': 'impression', 'at': iso_ago(hours=25)},
            {'slug': 'concert', 'type': 'clicked', 'at': iso_ago(minutes=-10)},
            {'slug': 'concert', 'type': 'page_viewed', 'at': iso_ago(minutes=-4)},
            {'slug': 'concert', 'type': 'dismissed', 'at': iso_ago(hours=23)},
        ]})
        self.assertEqual(response.json()['accepted'], 2)
        self.assertEqual(sorted(AnnouncementEvent.objects.values_list('type', flat=True)), ['dismissed', 'page_viewed'])

    def test_bad_bodies(self):
        self.assertEqual(self.client.post(EVENTS_URL, 'not json', content_type='text/plain').status_code, 400)
        self.assertEqual(self.post([1, 2]).status_code, 400)
        self.assertEqual(self.post({'device_id': 'a'}).json(), {'status': 'ok', 'accepted': 0, 'country': None})

    def test_an_empty_batch_tells_the_website_its_country(self):
        response = self.post({'device_id': 'web-1', 'events': []}, HTTP_CF_IPCOUNTRY='MD')
        self.assertEqual(response.json(), {'status': 'ok', 'accepted': 0, 'country': 'MD'})
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        unknown = self.post({'device_id': 'web-1', 'events': []}, HTTP_CF_IPCOUNTRY='XX')
        self.assertIsNone(unknown.json()['country'])

    def test_preflight(self):
        response = self.client.options(EVENTS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertIn('POST', response['Access-Control-Allow-Methods'])


@override_settings(CACHES=LOCMEM_CACHE)
class DeviceCountryTests(TestCase):
    URL = '/api/v1/devices/register/'

    def setUp(self):
        cache.clear()  # the registration rate limit lives in the cache

    def register(self, **headers):
        body = {'device_id': 'dev-1', 'platform': 'android', 'fcm_token': headers.pop('token', 'tok-1')}
        return self.client.post(self.URL, json.dumps(body), content_type='application/json', **headers)

    def test_country_is_stored_from_cloudflare_and_returned(self):
        response = self.register(HTTP_CF_IPCOUNTRY='md')
        self.assertEqual(response.json()['country'], 'MD')
        self.assertIsNone(self.register(HTTP_CF_IPCOUNTRY='XX').json()['country'])
        user = AppUsers.objects.get(anonymous_id='dev-1')
        self.assertEqual(user.device_country, 'MD')
        self.assertIsNotNone(user.device_push_token_updated_at)

    def test_unknown_countries_keep_the_last_known_one(self):
        self.register(HTTP_CF_IPCOUNTRY='RO')
        for unknown in ('XX', 'T1', '', 'ROU'):
            self.register(HTTP_CF_IPCOUNTRY=unknown)
            self.assertEqual(AppUsers.objects.get(anonymous_id='dev-1').device_country, 'RO', unknown)

    def test_token_timestamp_changes_only_with_the_token(self):
        self.register()
        first = AppUsers.objects.get(anonymous_id='dev-1').device_push_token_updated_at
        self.register()
        self.assertEqual(AppUsers.objects.get(anonymous_id='dev-1').device_push_token_updated_at, first)
        self.register(token='tok-2')
        self.assertGreater(AppUsers.objects.get(anonymous_id='dev-1').device_push_token_updated_at, first)


@override_settings(CACHES=LOCMEM_CACHE)
class EventsDedupeTests(TestCase):
    """Repeats from one device are dropped before they reach the counters."""

    def setUp(self):
        cache.clear()
        self.announcement = make_announcement('concert')
        self.clock = time.time()

    def report(self, *types, device_id='phone-1', seconds_later=0):
        events = [{'slug': 'concert', 'type': event_type} for event_type in types]
        with patch('time.time', return_value=self.clock + seconds_later):
            response = self.client.post(EVENTS_URL, json.dumps({'device_id': device_id, 'events': events}),
                                        content_type='text/plain', HTTP_CF_CONNECTING_IP=f'10.0.0.{seconds_later % 250}')
        return response.json()['accepted']

    def counters(self):
        self.announcement.refresh_from_db()
        return {name: getattr(self.announcement, name)
                for name in ('impressions', 'clicks', 'page_views', 'dismissals')}

    def test_impressions_once_per_device_per_30_minutes(self):
        self.assertEqual(self.report('impression', 'impression'), 1)
        self.assertEqual(self.report('impression', seconds_later=29 * 60), 0)
        self.assertEqual(self.report('impression', device_id='phone-2'), 1)
        self.assertEqual(self.report('impression', seconds_later=31 * 60), 1)
        self.assertEqual(self.counters()['impressions'], 3)

    def test_taps_once_per_device_and_type_per_minute(self):
        self.assertEqual(self.report('clicked', 'clicked', 'page_viewed'), 2)
        self.assertEqual(self.report('clicked', seconds_later=30), 0)
        self.assertEqual(self.report('clicked', seconds_later=61), 1)
        self.assertEqual(self.counters()['clicks'], 2)
        self.assertEqual(self.counters()['page_views'], 1)

    def test_closing_counts_once_per_device_from_the_database(self):
        self.assertEqual(self.report('dismissed', 'dismissed'), 1)
        cache.clear()  # no cache key involved: the stored close is what blocks a repeat
        self.assertEqual(self.report('dismissed', seconds_later=30 * 24 * 3600), 0)
        self.assertEqual(self.report('dismissed', device_id='phone-2'), 1)
        self.assertEqual(self.counters()['dismissals'], 2)
        self.assertEqual(AnnouncementEvent.objects.filter(type='dismissed').count(), 2)

    def test_the_database_refuses_a_second_close(self):
        from django.db import IntegrityError, transaction
        AnnouncementEvent.objects.create(announcement=self.announcement, type='dismissed', device_id='phone-1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            AnnouncementEvent.objects.create(announcement=self.announcement, type='dismissed', device_id='phone-1')

    def test_cache_keys_live_at_most_an_hour(self):
        from ..services.announcement_events import DEDUPE_SECONDS
        self.assertLessEqual(max(DEDUPE_SECONDS.values()), 3600)
        self.assertNotIn('dismissed', DEDUPE_SECONDS)


@override_settings(CACHES=LOCMEM_CACHE)
class EventsRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        make_announcement('concert')

    def post(self, device_id, ip):
        body = {'device_id': device_id, 'events': [{'slug': 'concert', 'type': 'clicked'}]}
        return self.client.post(EVENTS_URL, json.dumps(body), content_type='text/plain', HTTP_CF_CONNECTING_IP=ip)

    def limit(self, rate):
        return int(rate.split('/')[0])

    def test_per_ip_limit_leaves_room_for_shared_carrier_addresses(self):
        self.assertEqual(EVENTS_RATE_PER_IP, '600/m')

    @patch.object(announcements_api, 'EVENTS_RATE_PER_IP', '20/m')
    def test_per_ip(self):
        with patch('time.time', return_value=1_800_000_000):
            for index in range(20):
                self.assertEqual(self.post(f'device-{index}', '86.120.1.2').status_code, 200)
            response = self.post('one-more', '86.120.1.2')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Access-Control-Allow-Origin'], '*')
            self.assertFalse(AnnouncementEvent.objects.filter(device_id='one-more').exists())
            self.assertEqual(self.post('one-more', '86.120.9.9').status_code, 200)

    def test_per_device(self):
        with patch('time.time', return_value=1_800_000_000):
            for index in range(self.limit(EVENTS_RATE_PER_DEVICE)):
                self.assertEqual(self.post('phone-1', f'10.0.{index // 250}.{index % 250}').status_code, 200)
            self.assertEqual(self.post('phone-1', '10.9.9.9').status_code, 429)
            self.assertEqual(self.post('phone-2', '10.9.9.9').status_code, 200)
