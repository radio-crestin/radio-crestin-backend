from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import Announcement, AnnouncementSettings

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
LIST_URL = '/api/v1/announcements/'


def make_announcement(slug, **fields):
    defaults = {'title': slug, 'status': 'active', 'starts_at': timezone.now() - timedelta(hours=1)}
    defaults.update(fields)
    return Announcement.objects.create(slug=slug, **defaults)


@override_settings(CACHES=LOCMEM_CACHE)
class DragAndDropTests(TestCase):
    """The changelist reorder saves each row, so the cached list and its ETag change right away."""

    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        self.rows = [make_announcement(slug) for slug in ('a', 'b', 'c')]

    def reorder(self, slugs):
        """Posts the changelist form as Unfold's drag and drop leaves it (rows renumbered 0..n-1, then Save)."""
        by_slug = {row.slug: row for row in self.rows}
        data = {'form-TOTAL_FORMS': str(len(slugs)), 'form-INITIAL_FORMS': str(len(slugs)),
                'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000', '_save': 'Save'}
        for index, slug in enumerate(slugs):
            data[f'form-{index}-id'] = str(by_slug[slug].pk)
            data[f'form-{index}-position'] = str(index)
        return self.client.post(reverse('admin:radio_crestin_announcement_changelist'), data)

    def test_the_changelist_is_sortable_by_position(self):
        response = self.client.get(reverse('admin:radio_crestin_announcement_changelist'))
        self.assertContains(response, 'data-ordering-field="position"')
        self.assertContains(response, 'drag_indicator')

    def test_a_reorder_changes_the_api_order_and_etag(self):
        before = self.client.get(LIST_URL)
        self.assertEqual([item['slug'] for item in before.json()['announcements']], ['a', 'b', 'c'])

        self.assertEqual(self.reorder(['c', 'a', 'b']).status_code, 302)

        after = self.client.get(LIST_URL, HTTP_IF_NONE_MATCH=before['ETag'])
        self.assertEqual(after.status_code, 200)
        self.assertNotEqual(after['ETag'], before['ETag'])
        self.assertEqual([item['slug'] for item in after.json()['announcements']], ['c', 'a', 'b'])
        self.assertEqual([item['position'] for item in after.json()['announcements']], [0, 1, 2])


class AutoplaySettingTests(TestCase):
    def test_zero_or_three_to_sixty(self):
        settings = AnnouncementSettings.load()
        for seconds in (0, 3, 8, 60):
            settings.autoplay_seconds = seconds
            settings.full_clean()
        for seconds in (1, 2, 61, 600):
            settings.autoplay_seconds = seconds
            with self.assertRaises(ValidationError, msg=seconds):
                settings.full_clean()

    def test_off_by_default_and_sent_in_the_api(self):
        self.assertEqual(AnnouncementSettings().autoplay_seconds, 0)
        settings = AnnouncementSettings.load()
        settings.autoplay_seconds = 8
        settings.save()
        with override_settings(CACHES=LOCMEM_CACHE):
            cache.clear()
            self.assertEqual(self.client.get(LIST_URL).json()['settings']['autoplay_seconds'], 8)
