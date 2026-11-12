from datetime import timedelta
from unittest.mock import patch

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
    """The list's Save after a drag: the order changes in the API at once, even from a filtered or paged list."""

    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))
        self.rows = [make_announcement(slug) for slug in ('a', 'b', 'c')]

    def reorder(self, slugs, query=''):
        """Posts the list form as Unfold's drag and drop leaves it: the visible rows renumbered 0..n-1, then Save."""
        by_slug = {row.slug: row for row in Announcement.objects.all()}
        data = {'form-TOTAL_FORMS': str(len(slugs)), 'form-INITIAL_FORMS': str(len(slugs)),
                'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000', '_save': 'Save'}
        for index, slug in enumerate(slugs):
            data[f'form-{index}-id'] = str(by_slug[slug].pk)
            data[f'form-{index}-position'] = str(index)
        return self.client.post(reverse('admin:radio_crestin_announcement_changelist') + query, data)

    def order(self):
        return list(Announcement.objects.order_by('position', 'id').values_list('slug', 'position'))

    def test_the_changelist_is_sortable_by_position(self):
        response = self.client.get(reverse('admin:radio_crestin_announcement_changelist'))
        self.assertContains(response, 'data-ordering-field="position"')
        self.assertContains(response, 'drag_indicator')
        self.assertContains(response, 'Drag rows to change the order, then press Save')

    def test_a_filtered_reorder_keeps_the_hidden_rows(self):
        Announcement.objects.all().delete()
        for slug in ('home-1', 'station-1', 'home-2', 'station-2', 'home-3', 'station-3'):
            make_announcement(slug, placement='station' if slug.startswith('station') else 'home')
        query = '?placement__exact=station'
        response = self.reorder(['station-3', 'station-1', 'station-2'], query)
        self.assertRedirects(response, reverse('admin:radio_crestin_announcement_changelist') + query,
                             fetch_redirect_response=False)
        self.assertEqual(self.order(), [
            ('home-1', 0), ('station-3', 1), ('home-2', 2), ('station-1', 3), ('home-3', 4), ('station-2', 5),
        ])

    def test_a_reorder_on_page_two_leaves_page_one_alone(self):
        Announcement.objects.all().delete()
        for slug in ('p1-a', 'p1-b', 'p2-a', 'p2-b', 'p2-c'):
            make_announcement(slug)
        self.reorder(['p2-c', 'p2-a', 'p2-b'], '?p=2')
        self.assertEqual(self.order(), [('p1-a', 0), ('p1-b', 1), ('p2-c', 2), ('p2-a', 3), ('p2-b', 4)])

    def test_shared_positions_are_renumbered_first(self):
        Announcement.objects.all().delete()
        for slug in ('a', 'b', 'c', 'd'):
            make_announcement(slug)
        Announcement.objects.filter(slug__in=['b', 'c']).update(position=1)
        Announcement.objects.filter(slug='d').update(position=1)  # a=0, b=c=d=1
        self.reorder(['d', 'b'])  # a filtered view showing only b and d
        positions = [position for _, position in self.order()]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(self.order(), [('a', 0), ('d', 1), ('c', 2), ('b', 3)])

    def test_the_cache_is_dropped_once_per_save(self):
        from ..services import announcement_order
        with patch.object(announcement_order, 'invalidate_cache') as invalidate, \
                self.captureOnCommitCallbacks(execute=True):
            self.reorder(['c', 'b', 'a'])
        invalidate.assert_called_once_with()

    def test_a_reorder_changes_the_api_order_and_etag(self):
        before = self.client.get(LIST_URL)
        self.assertEqual([item['slug'] for item in before.json()['announcements']], ['a', 'b', 'c'])

        with self.captureOnCommitCallbacks(execute=True):  # the cache is dropped once the reorder commits
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
