from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import Announcement, AnnouncementCategory, AnnouncementImage, AnnouncementSettings
from ..services.announcement_feed import GENERATION_KEY
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
LIST_URL = '/api/v1/announcements/'
PUBLIC_CACHE_CONTROL = 'public, max-age=60, stale-while-revalidate=86400, stale-if-error=604800'
EXPECTED_FILTERS_KEYS = {'platforms', 'countries_include', 'countries_exclude', 'locales',
                         'min_app_version', 'max_app_version'}


def make_announcement(slug, **fields):
    defaults = {'title': slug, 'status': 'active', 'starts_at': timezone.now() - timedelta(hours=1)}
    defaults.update(fields)
    return Announcement.objects.create(slug=slug, **defaults)


def items(response):
    return response.json()['announcements']


def slugs(response):
    return [item['slug'] for item in items(response)]


@override_settings(CACHES=LOCMEM_CACHE)
class SeededAnnouncementTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_whatsapp_announcement_has_the_contract_shape(self):
        body = self.client.get(LIST_URL).json()

        self.assertEqual(body['settings'], {'rotation_mode': 'rotate', 'autoplay_seconds': 0, 'max_per_load': 5})
        whatsapp = body['announcements'][0]
        starts_at = whatsapp.pop('starts_at')
        self.assertTrue(starts_at.endswith('Z'))
        self.assertEqual(whatsapp, {
            'slug': 'whatsapp-versetul-zilei',
            'position': 0,
            'placement': 'home',
            'station_slugs': [],
            'category': {'slug': 'community', 'name': 'Comunitate', 'color': '#0F6E63', 'text_color': '#FFFFFF'},
            'icon': {'name': 'whatsapp'},
            'title': 'Versetul Zilei',
            'body_markdown': '',
            'body_html': '',
            'button': {
                'label': 'Primește-l zilnic pe WhatsApp', 'style': 'filled', 'icon': 'auto',
                'action': {'type': 'external', 'url': 'https://chat.whatsapp.com/I78qjRg1RaI5UKTvEwZdNm',
                           'web_target': 'new_tab'},
            },
            'dismissible': True,
            'filters': {'platforms': [], 'countries_include': [], 'countries_exclude': [], 'locales': [],
                        'min_app_version': None, 'max_app_version': None},
        })

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

    def test_cache_headers(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], PUBLIC_CACHE_CONTROL)
        for forbidden in ('s-maxage', 'no-cache', 'must-revalidate', 'private', 'no-store'):
            self.assertNotIn(forbidden, response['Cache-Control'])
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertTrue(response['ETag'].startswith('"'))

    def test_etag_answers_304_until_something_changes(self):
        make_announcement('concert')
        etag = self.client.get(LIST_URL)['ETag']

        not_modified = self.client.get(LIST_URL, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(not_modified.status_code, 304)
        self.assertEqual(not_modified['ETag'], etag)
        self.assertEqual(not_modified['Cache-Control'], PUBLIC_CACHE_CONTROL)
        self.assertEqual(not_modified['Access-Control-Allow-Origin'], '*')
        self.assertEqual(self.client.get(LIST_URL, HTTP_IF_NONE_MATCH=f'W/{etag}').status_code, 304)

        make_announcement('another')
        changed = self.client.get(LIST_URL, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(changed.status_code, 200)
        self.assertNotEqual(changed['ETag'], etag)

    def test_the_same_for_everyone(self):
        make_announcement('android-only', platforms=['android'], countries_include=['MD'], locales=['ro'],
                          min_app_version='1.6.0')
        plain = self.client.get(LIST_URL)
        with_params = self.client.get(LIST_URL, {'platform': 'web', 'device_id': 'x'}, HTTP_CF_IPCOUNTRY='DE')
        self.assertEqual(plain.content, with_params.content)
        self.assertEqual(items(plain)[0]['filters'], {
            'platforms': ['android'], 'countries_include': ['MD'], 'countries_exclude': [], 'locales': ['ro'],
            'min_app_version': '1.6.0', 'max_app_version': None,
        })

    def test_window_includes_the_next_7_days(self):
        now = timezone.now()
        make_announcement('live')
        make_announcement('next-week', starts_at=now + timedelta(days=6))
        make_announcement('later', starts_at=now + timedelta(days=8))
        make_announcement('draft', status='draft')
        make_announcement('preview', status='preview')
        make_announcement('ended', ends_at=now - timedelta(minutes=1))
        make_announcement('ending-later', ends_at=now + timedelta(days=1))
        self.assertEqual(sorted(slugs(self.client.get(LIST_URL))), ['ending-later', 'live', 'next-week'])

    def test_order_is_the_position(self):
        now = timezone.now()
        make_announcement('third', position=7, starts_at=now - timedelta(days=9))
        make_announcement('first', position=1, starts_at=now - timedelta(minutes=1))
        make_announcement('second', position=3)
        listed = items(self.client.get(LIST_URL))
        self.assertEqual([item['slug'] for item in listed], ['first', 'second', 'third'])
        self.assertEqual([item['position'] for item in listed], [1, 3, 7])
        self.assertNotIn('priority', listed[0])

    def test_a_new_announcement_goes_last(self):
        make_announcement('one')
        make_announcement('two')
        self.assertEqual(list(Announcement.objects.order_by('position').values_list('slug', 'position')),
                         [('one', 0), ('two', 1)])
        self.assertEqual(slugs(self.client.get(LIST_URL)), ['one', 'two'])

    def test_no_cap_on_the_count(self):
        # Clients apply max_per_load after their own filtering.
        settings = AnnouncementSettings.load()
        settings.max_per_load = 1
        settings.save()
        for index in range(3):
            make_announcement(f'a{index}')
        self.assertEqual(len(items(self.client.get(LIST_URL))), 3)

    def test_html_and_compact_payload(self):
        category = AnnouncementCategory.objects.get(slug='event')
        make_announcement(
            'concert', category=category, body_markdown='**Live** at *19:00*, [program](https://x.ro/p)',
            action_type='page', action_label='Program', button_style='outline', button_icon='calendar',
            button_text_color='#FFEE00', icon_name='calendar',
            page_title='Concert', page_markdown='# Program\n\n- 19:00 Opening',
        )
        item = items(self.client.get(LIST_URL))[0]
        self.assertEqual(
            item['body_html'],
            '<strong>Live</strong> at <em>19:00</em>, '
            '<a href="https://x.ro/p" target="_blank" rel="noopener noreferrer">program</a>',
        )
        self.assertEqual(item['button']['text_color'], '#FFEE00')  # set explicitly: sent
        self.assertNotIn('color', item['button'])  # no fallback to the category color
        self.assertEqual(item['category']['color'], '#7C3AED')
        self.assertEqual(item['button']['action'], {'type': 'page'})
        self.assertEqual(item['page'], {'title': 'Concert'})
        for absent in ('ends_at', 'hide_after_seconds', 'max_impressions'):
            self.assertNotIn(absent, item)

    def test_colors_are_sent_only_when_set(self):
        plain = AnnouncementCategory.objects.create(slug='plain', name='Simplu')
        make_announcement('themed', category=plain, action_type='external', action_label='Go',
                          action_url='https://example.com')
        make_announcement('painted', action_type='external', action_label='Go', action_url='https://example.com',
                          button_color='#0F6E63')
        by_slug = {item['slug']: item for item in items(self.client.get(LIST_URL))}

        self.assertEqual(by_slug['themed']['category'], {'slug': 'plain', 'name': 'Simplu'})
        self.assertNotIn('color', by_slug['themed']['button'])
        self.assertNotIn('text_color', by_slug['themed']['button'])
        # A button color gets its contrast label color unless one is set.
        self.assertEqual(by_slug['painted']['button']['color'], '#0F6E63')
        self.assertEqual(by_slug['painted']['button']['text_color'], '#FFFFFF')

    def test_absent_blocks_are_left_out(self):
        make_announcement('info', icon_name='info')
        item = items(self.client.get(LIST_URL))[0]
        for absent in ('button', 'page', 'category'):
            self.assertNotIn(absent, item)
        self.assertEqual(set(item['filters']), EXPECTED_FILTERS_KEYS)

    def test_hidden_button(self):
        make_announcement(
            'tap-card', action_type='external', action_url='https://example.com', button_style='hidden',
            button_color='#FFFFFF',
        )
        item = items(self.client.get(LIST_URL))[0]
        self.assertEqual(item['button']['style'], 'hidden')
        self.assertEqual(item['button']['text_color'], '#000000')

    def test_never_a_second_button(self):
        make_announcement('one-button', action_type='external', action_label='Go', action_url='https://example.com')
        self.assertNotIn('secondary_button', self.client.get(LIST_URL).content.decode())
        self.assertNotIn('secondary_button', self.client.get(f'{LIST_URL}one-button/').content.decode())

    def test_only_strict_slugs_are_sent(self):
        # Rows saved before the validator (or around it) are never sent.
        make_announcement('Old_Slug')
        make_announcement('fine', category=AnnouncementCategory.objects.create(slug='Bad Cat', name='x', color='#000000'),
                          placement='station')
        Announcement.objects.get(slug='fine').stations.add(make_station('ok-station'), make_station('bad slug!'))
        listed = items(self.client.get(LIST_URL))
        self.assertEqual([item['slug'] for item in listed], ['fine'])
        self.assertNotIn('category', listed[0])
        self.assertEqual(listed[0]['station_slugs'], ['ok-station'])
        self.assertEqual(self.client.get(f'{LIST_URL}Old_Slug/').status_code, 404)

    def test_station_announcements(self):
        elim = make_station('radio-elim', station_order=2.0)
        vocea = make_station('vocea', station_order=1.0)
        make_announcement('inside', placement='station').stations.add(elim, vocea)
        make_announcement('home')
        by_slug = {item['slug']: item for item in items(self.client.get(LIST_URL))}
        self.assertEqual(by_slug['inside']['placement'], 'station')
        self.assertEqual(by_slug['inside']['station_slugs'], ['vocea', 'radio-elim'])
        self.assertEqual(by_slug['home']['station_slugs'], [])


@override_settings(CACHES=LOCMEM_CACHE)
class CacheInvalidationTests(TestCase):
    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()

    def test_saving_or_deleting_drops_the_cached_list(self):
        announcement = make_announcement('cached')
        self.assertEqual(slugs(self.client.get(LIST_URL)), ['cached'])
        announcement.status = 'draft'
        announcement.save()
        self.assertEqual(slugs(self.client.get(LIST_URL)), [])
        announcement.status = 'active'
        announcement.save()
        self.assertEqual(slugs(self.client.get(LIST_URL)), ['cached'])
        announcement.delete()
        self.assertEqual(slugs(self.client.get(LIST_URL)), [])

    def test_categories_settings_and_stations_drop_it_too(self):
        category = AnnouncementCategory.objects.get(slug='event')
        announcement = make_announcement('concert', category=category, placement='station')
        self.client.get(LIST_URL)

        category.name = 'Concert'
        category.save()
        self.assertEqual(items(self.client.get(LIST_URL))[0]['category']['name'], 'Concert')

        settings = AnnouncementSettings.load()
        settings.max_per_load = 3
        settings.save()
        self.assertEqual(self.client.get(LIST_URL).json()['settings']['max_per_load'], 3)

        announcement.stations.add(make_station('radio-elim'))
        self.assertEqual(items(self.client.get(LIST_URL))[0]['station_slugs'], ['radio-elim'])

    def test_page_images_drop_the_cache(self):
        announcement = make_announcement('concert', page_title='Concert', page_markdown='Text')
        self.client.get(f'{LIST_URL}concert/')
        generation = cache.get(GENERATION_KEY)
        AnnouncementImage.objects.create(announcement=announcement, image='announcements/pages/choir.png')
        self.assertNotEqual(cache.get(GENERATION_KEY), generation)


@override_settings(CACHES=LOCMEM_CACHE)
class DetailEndpointTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_one_item_with_its_page_body(self):
        make_announcement(
            'concert', action_type='page', action_label='Program', page_title='Concert',
            page_markdown='## Program\n\n> Luke 2:11\n\n![Choir](https://cdn.x/choir.png)\n\n[bad](javascript:alert(1))',
        )
        response = self.client.get(f'{LIST_URL}concert/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], PUBLIC_CACHE_CONTROL)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        page = response.json()['page']
        self.assertEqual(page['markdown'][:10], '## Program')
        self.assertIn('<h2>Program</h2>', page['html'])
        self.assertIn('<blockquote>', page['html'])
        self.assertIn('<img alt="Choir" src="https://cdn.x/choir.png">', page['html'])
        self.assertNotIn('javascript', page['html'])
        self.assertEqual(self.client.get(f'{LIST_URL}concert/', HTTP_IF_NONE_MATCH=response['ETag']).status_code, 304)

    def test_404_when_not_active_not_started_ended_or_unknown(self):
        make_announcement('draft', status='draft')
        make_announcement('soon', starts_at=timezone.now() + timedelta(days=1))
        make_announcement('ended', ends_at=timezone.now() - timedelta(seconds=1))
        for slug in ('draft', 'soon', 'ended', 'missing'):
            response = self.client.get(f'{LIST_URL}{slug}/')
            self.assertEqual(response.status_code, 404, slug)
            self.assertEqual(response['Access-Control-Allow-Origin'], '*')


@override_settings(CACHES=LOCMEM_CACHE)
class PreviewTests(TestCase):
    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()
        self.token = AnnouncementSettings.load().preview_token
        make_announcement('live')
        make_announcement('preview', status='preview')
        make_announcement('draft', status='draft')

    def test_token_adds_preview_announcements_uncached(self):
        response = self.client.get(LIST_URL, {'preview': self.token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertNotIn('ETag', response)
        self.assertEqual(sorted(slugs(response)), ['live', 'preview'])
        self.assertEqual(slugs(self.client.get(LIST_URL)), ['live'])

    def test_wrong_or_empty_token_is_refused(self):
        for token in ('wrong', ''):
            response = self.client.get(LIST_URL, {'preview': token})
            self.assertEqual(response.status_code, 403, token)
            self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_preview_detail(self):
        self.assertEqual(self.client.get(f'{LIST_URL}preview/').status_code, 404)
        response = self.client.get(f'{LIST_URL}preview/', {'preview': self.token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_rotating_the_token_revokes_old_links(self):
        settings = AnnouncementSettings.load()
        settings.preview_token = 'rotated-token-value'
        settings.save()
        self.assertEqual(self.client.get(LIST_URL, {'preview': self.token}).status_code, 403)
        self.assertEqual(self.client.get(LIST_URL, {'preview': 'rotated-token-value'}).status_code, 200)

    def test_links(self):
        settings = AnnouncementSettings.load()
        self.assertEqual(settings.website_preview_url, f'https://www.radiocrestin.ro/?anunturi-preview={self.token}')
        self.assertEqual(settings.app_preview_url, f'radiocrestin://anunturi-preview?token={self.token}')
