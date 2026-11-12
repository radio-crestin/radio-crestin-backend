import json
import time
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import (
    Announcement, AnnouncementCategory, AnnouncementEvent, AnnouncementSettings, AppUsers,
)
from ..services.announcement_events import MAX_EVENTS_PER_REQUEST
from ..views.announcements_api import EVENTS_RATE_PER_DEVICE, EVENTS_RATE_PER_IP
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
LIST_URL = '/api/v1/announcements/'
EVENTS_URL = '/api/v1/announcements/events/'


def make_announcement(slug, **fields):
    defaults = {'title': slug, 'starts_at': timezone.now() - timedelta(hours=1)}
    defaults.update(fields)
    return Announcement.objects.create(slug=slug, **defaults)


def iso_ago(**delta):
    return (timezone.now() - timedelta(**delta)).isoformat().replace('+00:00', 'Z')


def slugs(response):
    return [item['slug'] for item in response.json()['announcements']]


@override_settings(CACHES=LOCMEM_CACHE)
class SeededAnnouncementTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_whatsapp_announcement_is_served_with_the_contract_shape(self):
        response = self.client.get(LIST_URL, {'platform': 'web', 'device_id': 'web-1'})
        body = response.json()

        self.assertEqual(body['settings'], {'rotation_mode': 'rotate', 'autoplay_seconds': 8, 'max_per_load': 5})
        whatsapp = body['announcements'][0]
        self.assertEqual(whatsapp['slug'], 'whatsapp-versetul-zilei')
        self.assertEqual(whatsapp['priority'], 10)
        self.assertEqual(whatsapp['category'], {
            'slug': 'community', 'name': 'Comunitate', 'color': '#0F6E63', 'text_color': '#FFFFFF',
        })
        self.assertEqual(whatsapp['icon'], {'name': 'whatsapp', 'url': None})
        self.assertEqual(whatsapp['title'], 'Versetul zilei pe WhatsApp zilnic la ora 7:30')
        self.assertEqual(whatsapp['body_markdown'], '')
        self.assertEqual(whatsapp['button'], {
            'label': 'Primește versetul zilei', 'style': 'filled', 'color': '#0F6E63',
            'text_color': '#FFFFFF', 'icon': 'auto',
            'action': {
                'type': 'external', 'url': 'https://chat.whatsapp.com/I78qjRg1RaI5UKTvEwZdNm',
                'web_target': 'new_tab', 'android_intent_uri': None, 'fallback_url': None, 'station_slug': None,
            },
        })
        self.assertIsNone(whatsapp['secondary_button'])
        self.assertIsNone(whatsapp['page'])
        self.assertTrue(whatsapp['dismissible'])
        self.assertTrue(whatsapp['starts_at'].endswith('Z'))
        self.assertIsNone(whatsapp['ends_at'])
        self.assertIsNone(whatsapp['hide_after_seconds'])
        self.assertIsNone(whatsapp['max_impressions'])

    def test_seeded_categories(self):
        self.assertEqual(
            list(AnnouncementCategory.objects.values_list('slug', 'color')),
            [('community', '#0F6E63'), ('event', '#7C3AED'), ('new', '#2563EB'),
             ('important', '#C2410C'), ('prayer', '#9D174D')],
        )


@override_settings(CACHES=LOCMEM_CACHE)
class ListEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()

    def get(self, **params):
        cache.clear()
        return self.client.get(LIST_URL, params)

    def test_headers(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

    def test_ordering_is_priority_then_newest_start(self):
        now = timezone.now()
        make_announcement('low', priority=1, starts_at=now - timedelta(days=1))
        make_announcement('high', priority=5, starts_at=now - timedelta(days=3))
        make_announcement('low-newer', priority=1, starts_at=now - timedelta(hours=1))
        self.assertEqual(slugs(self.get()), ['high', 'low-newer', 'low'])

    def test_time_window_and_active_flag(self):
        now = timezone.now()
        make_announcement('live')
        make_announcement('inactive', is_active=False)
        make_announcement('future', starts_at=now + timedelta(hours=1))
        make_announcement('ended', ends_at=now - timedelta(minutes=1))
        make_announcement('ending-later', ends_at=now + timedelta(days=1))
        self.assertEqual(sorted(slugs(self.get())), ['ending-later', 'live'])

    def test_max_per_load(self):
        settings = AnnouncementSettings.load()
        settings.max_per_load = 2
        settings.save()
        for index in range(4):
            make_announcement(f'a{index}', priority=index)
        response = self.get()
        self.assertEqual(slugs(response), ['a3', 'a2'])
        self.assertEqual(response.json()['settings']['max_per_load'], 2)

    def test_platform_and_viewport(self):
        make_announcement('phones-web', platforms=['web_mobile'])
        make_announcement('android', platforms=['android'])
        self.assertEqual(slugs(self.get(platform='web', viewport='mobile')), ['phones-web'])
        self.assertEqual(slugs(self.get(platform='web', viewport='desktop')), [])
        self.assertEqual(slugs(self.get(platform='web')), ['phones-web'])
        self.assertEqual(slugs(self.get(platform='android', app_version='1.6.2')), ['android'])

    def test_country_from_cloudflare_header(self):
        make_announcement('moldova', countries_include=['MD'])
        self.assertEqual(slugs(self.client.get(LIST_URL, HTTP_CF_IPCOUNTRY='MD')), ['moldova'])
        cache.clear()
        self.assertEqual(slugs(self.client.get(LIST_URL, HTTP_CF_IPCOUNTRY='RO')), [])

    def test_ip_range_uses_the_client_ip(self):
        make_announcement('office', ip_ranges=['86.120.0.0/16'])
        self.assertEqual(slugs(self.client.get(LIST_URL, HTTP_CF_CONNECTING_IP='86.120.1.2')), ['office'])
        cache.clear()
        self.assertEqual(slugs(self.client.get(LIST_URL, HTTP_CF_CONNECTING_IP='1.1.1.1')), [])

    def test_locale_and_app_version(self):
        make_announcement('romanian', locales=['ro'])
        make_announcement('update', max_app_version='1.5.99', platforms=['android', 'ios'])
        self.assertEqual(sorted(slugs(self.get(locale='ro_RO', platform='android', app_version='1.5.0'))),
                         ['romanian', 'update'])
        self.assertEqual(slugs(self.get(locale='ro-RO', platform='web')), ['romanian'])
        self.assertEqual(slugs(self.get(locale='en-US', platform='android', app_version='1.6.2')), [])

    def test_picked_and_pasted_device_ids(self):
        phone = AppUsers.objects.create(anonymous_id='phone-1')
        announcement = make_announcement('testers', extra_device_ids=['web-9'])
        announcement.target_devices.add(phone)
        self.assertEqual(slugs(self.get(device_id='phone-1')), ['testers'])
        self.assertEqual(slugs(self.get(device_id='web-9')), ['testers'])
        self.assertEqual(slugs(self.get(device_id='someone-else')), [])

    def test_missing_app_version_is_fine(self):
        make_announcement('any')
        response = self.client.get(LIST_URL, {'platform': 'web', 'device_id': 'w', 'locale': 'ro-RO'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(slugs(response), ['any'])

    def test_buttons_and_page(self):
        category = AnnouncementCategory.objects.get(slug='event')
        station = make_station('radio-elim')
        make_announcement(
            'concert', category=category, body_markdown='**Live**',
            action_type='page', action_label='Program', button_style='outline', button_icon='calendar',
            button_text_color='#FFEE00',
            secondary_kind='action', secondary_label='Listen', secondary_action_type='station',
            secondary_station=station,
            page_title='Concert', page_markdown='# Program',
        )
        item = self.get().json()['announcements'][0]
        self.assertEqual(item['button']['style'], 'outline')
        self.assertEqual(item['button']['color'], '#7C3AED')
        self.assertEqual(item['button']['text_color'], '#FFEE00')
        self.assertEqual(item['button']['icon'], 'calendar')
        self.assertEqual(item['button']['action']['type'], 'page')
        self.assertEqual(item['secondary_button'], {
            'label': 'Listen', 'kind': 'action', 'later_days': None,
            'action': {'type': 'station', 'url': None, 'web_target': 'new_tab', 'android_intent_uri': None,
                       'fallback_url': None, 'station_slug': 'radio-elim'},
        })
        self.assertEqual(item['page'], {'title': 'Concert', 'cover_image_url': None, 'markdown': '# Program'})

    def test_hidden_button_and_later_secondary(self):
        make_announcement(
            'tap-card', action_type='external', action_url='https://example.com', button_style='hidden',
            button_color='#FFFFFF', secondary_kind='later', secondary_label='Later', secondary_later_days=3,
        )
        item = self.get().json()['announcements'][0]
        self.assertEqual(item['button']['style'], 'hidden')
        self.assertEqual(item['button']['label'], '')
        self.assertEqual(item['button']['text_color'], '#000000')
        self.assertEqual(item['secondary_button'], {'label': 'Later', 'kind': 'later', 'later_days': 3, 'action': None})

    def test_no_button(self):
        make_announcement('info')
        item = self.get().json()['announcements'][0]
        self.assertIsNone(item['button'])
        self.assertIsNone(item['category'])

    def test_station_announcements_are_listed_alongside_home_ones(self):
        elim = make_station('radio-elim', station_order=2.0)
        vocea = make_station('vocea', station_order=1.0)
        inside = make_announcement('inside', placement='station', priority=9)
        inside.stations.add(elim, vocea)
        make_announcement('home')
        items = {item['slug']: item for item in self.get(platform='android').json()['announcements']}
        self.assertEqual(items['inside']['placement'], 'station')
        self.assertEqual(items['inside']['station_slugs'], ['vocea', 'radio-elim'])
        self.assertEqual(items['home']['placement'], 'home')
        self.assertEqual(items['home']['station_slugs'], [])

    def test_max_per_load_caps_only_the_home_card(self):
        settings = AnnouncementSettings.load()
        settings.max_per_load = 1
        settings.save()
        station = make_station('radio-elim')
        for index in range(3):
            make_announcement(f'home{index}', priority=index)
            make_announcement(f'station{index}', placement='station', priority=index).stations.add(station)
        listed = slugs(self.get())
        self.assertEqual([slug for slug in listed if slug.startswith('home')], ['home2'])
        self.assertEqual([slug for slug in listed if slug.startswith('station')], ['station2', 'station1', 'station0'])

    def test_linking_a_station_drops_the_cached_list(self):
        inside = make_announcement('inside', placement='station')
        self.assertEqual(self.client.get(LIST_URL).json()['announcements'][0]['station_slugs'], [])
        inside.stations.add(make_station('radio-elim'))
        self.assertEqual(self.client.get(LIST_URL).json()['announcements'][0]['station_slugs'], ['radio-elim'])

    def test_saving_in_the_admin_drops_the_cached_list(self):
        announcement = make_announcement('cached')
        self.assertEqual(slugs(self.client.get(LIST_URL)), ['cached'])
        announcement.is_active = False
        announcement.save()
        self.assertEqual(slugs(self.client.get(LIST_URL)), [])


@override_settings(CACHES=LOCMEM_CACHE)
class DetailEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_returns_one_item_without_targeting(self):
        make_announcement('android-only', platforms=['android'], countries_include=['RO'])
        response = self.client.get(f'{LIST_URL}android-only/', {'platform': 'web'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slug'], 'android-only')
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

    def test_404_when_inactive_ended_or_unknown(self):
        make_announcement('off', is_active=False)
        make_announcement('ended', ends_at=timezone.now() - timedelta(seconds=1))
        for slug in ('off', 'ended', 'missing'):
            self.assertEqual(self.client.get(f'{LIST_URL}{slug}/').status_code, 404, slug)


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
        self.assertEqual(response.json(), {'status': 'ok', 'accepted': 6})
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
        self.assertEqual(response.json(), {'status': 'ok', 'accepted': 1})
        event = AnnouncementEvent.objects.get()
        self.assertEqual((event.target, event.position), ('', None))

    def test_at_most_100_events_are_read(self):
        Announcement.objects.bulk_create([
            Announcement(slug=f'bulk-{index}', title='bulk') for index in range(MAX_EVENTS_PER_REQUEST + 20)
        ])
        events = [{'slug': f'bulk-{index}', 'type': 'impression'} for index in range(MAX_EVENTS_PER_REQUEST + 20)]
        response = self.post({'device_id': 'a', 'events': events})
        self.assertEqual(response.json()['accepted'], MAX_EVENTS_PER_REQUEST)
        self.assertEqual(Announcement.objects.filter(slug__startswith='bulk-', impressions=1).count(),
                         MAX_EVENTS_PER_REQUEST)

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
        self.assertEqual(self.post({'device_id': 'a'}).json(), {'status': 'ok', 'accepted': 0})

    def test_preflight(self):
        response = self.client.options(EVENTS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertIn('POST', response['Access-Control-Allow-Methods'])


class DeviceCountryTests(TestCase):
    URL = '/api/v1/devices/register/'

    def register(self, **headers):
        body = {'device_id': 'dev-1', 'platform': 'android', 'fcm_token': headers.pop('token', 'tok-1')}
        return self.client.post(self.URL, json.dumps(body), content_type='application/json', **headers)

    def test_country_is_stored_from_cloudflare(self):
        self.register(HTTP_CF_IPCOUNTRY='md')
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

    def test_closing_counts_once_per_device(self):
        self.assertEqual(self.report('dismissed'), 1)
        self.assertEqual(self.report('dismissed', seconds_later=30 * 24 * 3600), 0)
        self.assertEqual(self.counters()['dismissals'], 1)


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

    def test_per_ip(self):
        with patch('time.time', return_value=1_800_000_000):
            for index in range(self.limit(EVENTS_RATE_PER_IP)):
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
