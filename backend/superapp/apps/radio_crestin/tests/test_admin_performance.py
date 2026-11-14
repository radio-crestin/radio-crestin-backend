import itertools
import os
import random
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import Promise

from superapp.apps.admin_portal.sites import superapp_admin_site

from ..models import Announcement, AnnouncementEvent, AppUsers
from ..services import announcement_push
from ..services.announcement_feed import rules_for
from ..services.announcement_targeting import Audience, compare_versions, matches
from ..utils.app_versions import version_code

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CONFIGURED = {announcement_push.CREDENTIALS_ENV: '{"type": "service_account"}'}
VERSIONS = ['1.4.3', '1.5', '1.5.0', '1.6.0', '1.6.2', '1.7.0+56', '1.10.0', 'v2.0', '1.6.0.1', 'beta', '', None]
LOCALES = ['ro_RO', 'ro-RO', 'RO', 'ro-md', 'en_US', 'en', 'hu-HU', 'rom', '', None]
COUNTRIES = ['RO', 'MD', 'DE', 'IT', None]
PLATFORMS = ['android', 'Android', 'ios', 'iOS', 'web', None]


class VersionCodeTests(SimpleTestCase):
    def test_sorts_like_the_versions(self):
        readable = [v for v in VERSIONS if version_code(v) is not None]
        for left, right in itertools.product(readable, repeat=2):
            code_order = (version_code(left) > version_code(right)) - (version_code(left) < version_code(right))
            self.assertEqual(code_order, compare_versions(left, right), (left, right))

    def test_unreadable_versions_have_no_code(self):
        for version in ('beta', '', None):
            self.assertIsNone(version_code(version))


class VersionCodeColumnTests(TestCase):
    def test_kept_in_sync_on_save_and_registration(self):
        user = AppUsers.objects.create(anonymous_id='phone-1', device_app_version='1.6.2')
        self.assertEqual(user.device_app_version_code, version_code('1.6.2'))
        user.device_app_version = '1.7.0'
        user.save(update_fields=['device_app_version'])
        user.refresh_from_db()
        self.assertEqual(user.device_app_version_code, version_code('1.7.0'))

        self.client.post('/api/v1/devices/register/', '{"device_id": "phone-1", "app_version": "1.10.0"}',
                         content_type='application/json')
        user.refresh_from_db()
        self.assertEqual(user.device_app_version_code, version_code('1.10.0'))


class SqlAudienceTests(TestCase):
    """The SQL audience picks exactly the devices the targeting rules (the clients' rules) pick."""

    @classmethod
    def setUpTestData(cls):
        rng = random.Random(11)
        AppUsers.objects.bulk_create([
            AppUsers(anonymous_id=f'device-{index}', email=f'device-{index}@example.invalid',
                     device_platform=rng.choice(PLATFORMS), device_locale=rng.choice(LOCALES),
                     device_country=rng.choice(COUNTRIES), device_app_version=(version := rng.choice(VERSIONS)),
                     device_app_version_code=version_code(version),
                     device_fcm_token=rng.choice(['', None, f'token-{index}', f'token-{index}']))
            for index in range(600)
        ])

    def python_audience(self, announcement):
        rules = rules_for(announcement)
        picked = set()
        for user in AppUsers.objects.filter(anonymous_id__startswith='device-'):
            platform = (user.device_platform or '').lower()
            if platform not in ('android', 'ios'):
                continue
            audience = Audience(platform=platform, country=user.device_country or '', locale=user.device_locale or '',
                                app_version=user.device_app_version or '')
            if matches(rules, audience):
                picked.add(user.id)
        return picked

    def test_same_devices_as_the_rules(self):
        cases = [
            {},
            {'platforms': ['ios']},
            {'platforms': ['web_mobile']},
            {'countries_include': ['RO', 'MD']},
            {'countries_exclude': ['DE']},
            {'locales': ['ro']},
            {'locales': ['ro-RO', 'hu']},
            {'min_app_version': '1.6.0'},
            {'max_app_version': '1.5.0'},
            {'min_app_version': '1.6', 'max_app_version': '1.10.0', 'locales': ['ro'], 'countries_exclude': ['IT']},
            {'min_app_version': 'not a version'},
        ]
        for index, filters in enumerate(cases):
            announcement = Announcement.objects.create(slug=f'case-{index}', title='x', **filters)
            sql = set(announcement_push.audience(announcement).filter(anonymous_id__startswith='device-')
                      .values_list('id', flat=True))
            self.assertEqual(sql, self.python_audience(announcement), filters)

    def test_reach_is_one_query_and_counts_tokens_per_platform(self):
        announcement = Announcement.objects.create(slug='all', title='x', locales=['ro'])
        with self.assertNumQueries(1):
            counts = announcement_push.reach(announcement)
        devices = self.python_audience(announcement)
        users = AppUsers.objects.filter(id__in=devices)
        with_token = [u for u in users if u.device_fcm_token]
        self.assertEqual(counts['android'], sum(u.device_platform.lower() == 'android' for u in with_token))
        self.assertEqual(counts['ios'], sum(u.device_platform.lower() == 'ios' for u in with_token))
        self.assertEqual(counts['without_token'], len(devices) - len(with_token))
        self.assertEqual(counts['total'], len(with_token))

    def test_sending_reads_devices_in_pages_without_a_cursor(self):
        announcement = Announcement.objects.create(slug='paged', title='x')
        expected = set(AppUsers.objects.filter(anonymous_id__startswith='device-', device_platform__iregex='^(android|ios)$')
                       .exclude(device_fcm_token__isnull=True).exclude(device_fcm_token='').values_list('id', flat=True))
        with patch.object(announcement_push, 'PAGE_SIZE', 50), \
                patch('django.db.models.query.QuerySet.iterator', side_effect=AssertionError('no iterator')):
            devices = list(announcement_push.matching_devices(announcement))
        self.assertEqual({device.id for device in devices}, expected)
        self.assertTrue(all(device.token for device in devices))


class DatabaseSettingsTests(SimpleTestCase):
    def test_no_server_side_cursors_through_pgbouncer(self):
        if 'DISABLE_SERVER_SIDE_CURSORS' not in settings.DATABASES['default'] and not os.environ.get('DATABASE_URL'):
            self.skipTest('SQLite settings')
        self.assertIs(settings.DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'], True)


@override_settings(CACHES=LOCMEM_CACHE)
class AdminQueryCountTests(TestCase):
    """The pages cost the same number of queries however many devices and events there are."""

    def setUp(self):
        cache.clear()
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        self.announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')

    def grow(self, devices, events):
        start = AppUsers.objects.count()
        AppUsers.objects.bulk_create([
            AppUsers(anonymous_id=f'grow-{start + index}', email=f'grow-{start + index}@example.invalid',
                     device_platform='android', device_fcm_token=f'token-{start + index}')
            for index in range(devices)
        ])
        AnnouncementEvent.objects.bulk_create([
            AnnouncementEvent(announcement=self.announcement, type=kind, device_id=f'grow-{index}', platform='web')
            for index in range(events) for kind in ('impression', 'clicked')
        ])

    def count_queries(self, url):
        self.client.get(url)  # the first request warms per-process caches
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(url).status_code, 200)
        return len(queries)

    def test_change_page(self):
        url = reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,))
        with patch.dict(os.environ, CONFIGURED):
            self.grow(devices=20, events=20)
            small = self.count_queries(url)
            self.grow(devices=400, events=300)
            with self.assertNumQueries(small):
                self.client.get(url)
        self.assertLessEqual(small, 22)  # includes the two History reads (stat buckets)

    def test_changelist(self):
        url = reverse('admin:radio_crestin_announcement_changelist')
        small = self.count_queries(url)
        for index in range(15):
            Announcement.objects.create(slug=f'more-{index}', title='x', status='active',
                                        starts_at=timezone.now() - timedelta(hours=1))
        self.grow(devices=100, events=100)
        with self.assertNumQueries(small):
            self.client.get(url)
        self.assertLessEqual(small, 15)

    def test_app_users_changelist(self):
        url = reverse('admin:radio_crestin_appusers_changelist')
        self.grow(devices=30, events=0)
        small = self.count_queries(url)
        self.grow(devices=300, events=0)
        with self.assertNumQueries(small):
            self.client.get(url)


@override_settings(CACHES=LOCMEM_CACHE)
class AnnouncementChangePageWorkTests(TestCase):
    """The change page skips the work it does not show: list-only counts, and the reach (fetched after load)."""

    def setUp(self):
        cache.clear()
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        self.announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')
        self.reach_url = reverse('admin:radio_crestin_announcement_push_reach', args=(self.announcement.pk,))
        AppUsers.objects.bulk_create([
            AppUsers(anonymous_id=f'reach-{index}', email=f'reach-{index}@example.invalid',
                     device_platform=platform, device_fcm_token=f'token-{index}' if index % 3 else '')
            for index, platform in enumerate(['android', 'ios'] * 6)
        ])

    def test_change_page_leaves_out_reach_and_list_counts(self):
        url = reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,))
        with patch.dict(os.environ, CONFIGURED), CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertContains(response, f'data-after-load="{self.reach_url}"')
        results_url = reverse('admin:radio_crestin_announcement_results', args=(self.announcement.pk,))
        self.assertContains(response, f'data-after-load="{results_url}"', count=2)  # results and breakdown
        sql = [query['sql'] for query in queries]
        self.assertFalse([q for q in sql if 'FROM "announcement_events"' in q], 'events are counted on the page')
        self.assertFalse([q for q in sql if 'FROM "app_users"' in q and 'COUNT(' in q], 'the reach is counted on the page')
        self.assertFalse([q for q in sql if q.startswith('SELECT "announcements"') and 'announcement_events' in q],
                         'the change page annotates the list-only unique counts')

    def test_push_reach_endpoint(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.reach_url)
        self.assertEqual(response.status_code, 200)
        own = [q['sql'] for q in queries if 'FROM "announcements"' in q['sql'] or 'FROM "app_users"' in q['sql']]
        self.assertEqual(len(own), 2, own)  # the announcement, and the reach as one aggregate
        self.assertIn('no-store', response['Cache-Control'])
        body = response.json()
        expected = announcement_push.reach(self.announcement)
        self.assertEqual({key: body[key] for key in expected}, expected)
        self.assertIn('Reach:', body['text'])

    def test_results_endpoint(self):
        from ..models import AnnouncementEvent
        for device_id in ('a', 'a', 'b'):
            AnnouncementEvent.objects.create(announcement=self.announcement, type='impression', device_id=device_id)
        AnnouncementEvent.objects.create(announcement=self.announcement, type='clicked', device_id='a', target='card')
        response = self.client.get(reverse('admin:radio_crestin_announcement_results', args=(self.announcement.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        body = response.json()
        self.assertIn('50.0%', body['stats'])           # 1 unique clicker of 2 unique viewers
        self.assertIn('Unique devices', body['stats'])
        self.assertIn('impression', body['events'])
        self.assertIn('card 1', body['events'])

    def test_results_endpoint_needs_admin(self):
        self.client.logout()
        response = self.client.get(reverse('admin:radio_crestin_announcement_results', args=(self.announcement.pk,)))
        self.assertEqual(response.status_code, 302)

    def test_push_reach_needs_view_permission(self):
        staff = get_user_model().objects.create_user(email='staff@example.com', password='x')
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.reach_url).status_code, 403)

    def test_changelist_still_shows_unique_counts(self):
        AnnouncementEvent.objects.bulk_create([
            AnnouncementEvent(announcement=self.announcement, type='impression', device_id=f'viewer-{index}', platform='web')
            for index in range(7)
        ])
        response = self.client.get(reverse('admin:radio_crestin_announcement_changelist'))
        self.assertEqual(response.context['cl'].result_list.get(pk=self.announcement.pk).unique_viewers, 7)


class SidebarLinkTests(TestCase):
    def test_sidebar_links_are_resolved_once(self):
        request = RequestFactory().get('/portal/')
        request.user = get_user_model().objects.create_superuser(email='admin@example.com', password='x')
        sidebar = superapp_admin_site._get_config('SIDEBAR', request)
        links = [item.get('link') for group in sidebar.get('navigation') or [] for item in group.get('items', [])]
        self.assertTrue(links)
        self.assertFalse([link for link in links if isinstance(link, Promise)])

        changelist = reverse('admin:radio_crestin_announcement_changelist')
        self.client.force_login(request.user)
        self.assertContains(self.client.get(changelist), f'href="{changelist}"')

    def test_sidebar_is_only_the_configured_navigation(self):
        request = RequestFactory().get('/portal/')
        request.user = get_user_model().objects.create_superuser(email='admin@example.com', password='x')
        sidebar = superapp_admin_site._get_config('SIDEBAR', request)
        tabs = superapp_admin_site._get_config('TABS', request) or []
        links = {str(item.get('link')) for group in [*(sidebar.get('navigation') or []), *tabs] for item in group.get('items', [])}

        self.assertFalse(sidebar.get('show_all_applications'))
        self.assertFalse([link for link in links if 'posthog' in link])
        links = {link.split('?')[0] for link in links}
        linked_elsewhere = {'radio_crestin_sharelinkvisit'}  # from each share link's visit count
        unreachable = [
            f'{model._meta.app_label}_{model._meta.model_name}'
            for model in superapp_admin_site._registry
            if f'{model._meta.app_label}_{model._meta.model_name}' not in linked_elsewhere
            and reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist') not in links
        ]
        self.assertEqual(unreachable, [])


class ChangeformDataTests(TestCase):
    """The faster changeform_data (admin_portal.unfold_patches) gives Unfold's exact output."""

    def test_same_x_data_as_unfold_without_running_readonly_fields(self):
        import json
        from unfold.templatetags import unfold as unfold_tags
        from superapp.apps.admin_portal import unfold_patches

        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')
        response = self.client.get(reverse('admin:radio_crestin_announcement_change', args=(announcement.pk,)))
        adminform = response.context['adminform']
        self.assertIs(unfold_tags.register.filters['changeform_data'], unfold_patches.changeform_data)
        self.assertEqual(json.loads(unfold_patches.changeform_data(adminform)),
                         json.loads(unfold_tags.changeform_data(adminform)))
        with patch.object(type(adminform.model_admin), 'history_display', side_effect=AssertionError('ran')):
            unfold_patches.changeform_data(adminform)
