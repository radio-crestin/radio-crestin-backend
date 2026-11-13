import itertools
import os
import random
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

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
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
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
        self.assertLessEqual(small, 20)

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
