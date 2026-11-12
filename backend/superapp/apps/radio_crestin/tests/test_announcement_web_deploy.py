import os
from datetime import timedelta
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from ..models import Announcement, AnnouncementCategory
from ..services import web_deploy
from ..tasks.trigger_web_deploy import trigger_web_deploy

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
HOOK = {web_deploy.HOOK_URL_ENV: 'https://api.cloudflare.example/pages/webhooks/deploy_hooks/abc'}
APPLY_ASYNC = 'superapp.apps.radio_crestin.tasks.trigger_web_deploy.trigger_web_deploy.apply_async'


def make_announcement(slug='concert', **fields):
    defaults = {'title': slug, 'status': 'active', 'starts_at': timezone.now() - timedelta(hours=1)}
    defaults.update(fields)
    return Announcement.objects.create(slug=slug, **defaults)


@override_settings(CACHES=LOCMEM_CACHE)
class ScheduleTests(TestCase):
    def setUp(self):
        cache.clear()
        Announcement.objects.all().delete()
        cache.clear()

    def changes(self, change):
        """Runs `change` with the hook configured; returns the countdowns of the queued builds."""
        with patch.dict(os.environ, HOOK), patch(APPLY_ASYNC) as apply_async, \
                self.captureOnCommitCallbacks(execute=True):
            change()
        return [call.kwargs['countdown'] for call in apply_async.call_args_list]

    def test_a_website_announcement_schedules_one_debounced_build(self):
        def change():
            make_announcement('one')
            make_announcement('two', platforms=['web_mobile'])
        self.assertEqual(self.changes(change), [web_deploy.DEBOUNCE_SECONDS])

    def test_app_only_and_draft_announcements_do_not(self):
        def change():
            make_announcement('android', platforms=['android', 'ios'])
            make_announcement('draft', status='draft')
        self.assertEqual(self.changes(change), [])

    def test_hiding_or_deleting_a_website_announcement_does(self):
        announcement = make_announcement()
        cache.clear()

        def deactivate():
            announcement.status = 'draft'
            announcement.save()
        self.assertEqual(len(self.changes(deactivate)), 1)

        announcement.status = 'active'
        announcement.save()
        cache.clear()
        self.assertEqual(len(self.changes(announcement.delete)), 1)

    def test_category_changes_rebuild_when_the_website_shows_announcements(self):
        make_announcement()
        cache.clear()
        category = AnnouncementCategory.objects.get(slug='event')

        def rename():
            category.name = 'Concert'
            category.save()
        self.assertEqual(len(self.changes(rename)), 1)

    def test_skipped_without_a_hook_url(self):
        with patch.dict(os.environ, {web_deploy.HOOK_URL_ENV: ''}), patch(APPLY_ASYNC) as apply_async, \
                self.captureOnCommitCallbacks(execute=True):
            make_announcement()
        apply_async.assert_not_called()


@override_settings(CACHES=LOCMEM_CACHE)
class TriggerTaskTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_posts_the_hook_and_lets_new_changes_schedule_again(self):
        cache.set(web_deploy.PENDING_KEY, 1)
        with patch.dict(os.environ, HOOK), patch('requests.post') as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            self.assertEqual(trigger_web_deploy(), {'success': True, 'status_code': 200})
        post.assert_called_once_with(HOOK[web_deploy.HOOK_URL_ENV], timeout=15)
        self.assertIsNone(cache.get(web_deploy.PENDING_KEY))

    def test_network_errors_are_logged_not_raised(self):
        with patch.dict(os.environ, HOOK), patch('requests.post', side_effect=requests.ConnectionError('down')):
            self.assertFalse(trigger_web_deploy()['success'])

    def test_skips_without_a_hook_url(self):
        with patch.dict(os.environ, {web_deploy.HOOK_URL_ENV: ''}), patch('requests.post') as post:
            self.assertFalse(trigger_web_deploy()['success'])
        post.assert_not_called()
