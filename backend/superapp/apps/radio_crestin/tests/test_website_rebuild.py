import os
from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import StationGroups, StationStreams, Stations, StationToStationGroup
from ..services import web_deploy
from ..tasks.trigger_web_deploy import trigger_web_deploy
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
HOOK = {web_deploy.HOOK_URL_ENV: 'https://deploy-hook.example/fake-hook'}
APPLY_ASYNC = 'superapp.apps.radio_crestin.tasks.trigger_web_deploy.trigger_web_deploy.apply_async'
NOW = 1_800_000_000


@override_settings(CACHES=LOCMEM_CACHE)
class StationChangesTests(TestCase):
    def setUp(self):
        self.station = make_station('radio-elim')
        self.group = StationGroups.objects.create(slug='popular', name='Populare')
        self.stream = StationStreams.objects.create(station=self.station, stream_url='https://s.example/a', type='HLS')
        cache.clear()

    @contextmanager
    def builds(self):
        """Collects the countdowns of the builds queued inside the block."""
        countdowns = []
        with patch.dict(os.environ, HOOK), patch('time.time', return_value=NOW), patch(APPLY_ASYNC) as apply_async, \
                self.captureOnCommitCallbacks(execute=True):
            yield countdowns
        countdowns.extend(call.kwargs['countdown'] for call in apply_async.call_args_list)

    def reload(self):
        return Stations.objects.get(pk=self.station.pk)

    def test_scraper_uptime_and_now_playing_writes_never_build(self):
        with self.builds() as countdowns:
            Stations.objects.filter(pk=self.station.pk).update(latest_station_now_playing=None, latest_station_uptime=None)
            station = self.reload()
            station.save(update_fields=['latest_station_now_playing'])
            station.save(update_fields=['latest_station_uptime', 'config_version'])
            station.metadata_scrape_interval = 30
            station.check_uptime = False
            station.save()  # a full save that changes no website field
        self.assertEqual(countdowns, [])

    def test_title_thumbnail_and_stream_changes_build_once(self):
        with self.builds() as countdowns:
            station = self.reload()
            station.title = 'Radio Elim Plus'
            station.save()
            station.thumbnail = 'stations/elim.png'
            station.save()
            self.stream.stream_url = 'https://s.example/b'
            self.stream.save()
        self.assertEqual(countdowns, [web_deploy.DEBOUNCE_SECONDS])

    def test_each_kind_of_website_change_builds(self):
        def title():
            station = self.reload()
            station.title = 'Nou'
            station.save()

        def thumbnail():
            station = self.reload()
            station.thumbnail = 'stations/elim-new.png'
            station.save()

        def hide():
            station = self.reload()
            station.disabled = True
            station.save(update_fields=['disabled'])

        def stream_off():
            self.stream.enabled = False
            self.stream.save()

        def new_stream():
            StationStreams.objects.create(station=self.station, stream_url='https://s.example/c', type='HLS')

        def group_name():
            self.group.name = 'Cele mai ascultate'
            self.group.save()

        def membership():
            StationToStationGroup.objects.create(station=self.station, group=self.group)

        def m2m_add():
            self.station.groups.add(self.group)

        def delete_stream():
            self.stream.delete()

        for change in (title, thumbnail, hide, stream_off, new_stream, group_name, membership, m2m_add, delete_stream):
            cache.clear()
            with self.builds() as countdowns:
                change()
            self.assertEqual(len(countdowns), 1, change.__name__)

    def test_nothing_without_a_hook_url(self):
        with patch.dict(os.environ, {web_deploy.HOOK_URL_ENV: ''}), patch(APPLY_ASYNC) as apply_async, \
                self.captureOnCommitCallbacks(execute=True):
            station = self.reload()
            station.title = 'Nou'
            station.save()
        apply_async.assert_not_called()


@override_settings(CACHES=LOCMEM_CACHE)
class CoalescingTests(TestCase):
    def setUp(self):
        self.station = make_station('radio-elim')
        cache.clear()

    def change(self, title):
        station = Stations.objects.get(pk=self.station.pk)
        station.title = title
        station.save()

    def burst(self, at, count=20):
        with patch('time.time', return_value=at), patch(APPLY_ASYNC) as apply_async, \
                self.captureOnCommitCallbacks(execute=True):
            for index in range(count):
                self.change(f'Radio Elim {at} {index}')
        return [call.kwargs['countdown'] for call in apply_async.call_args_list]

    def run_task(self, at):
        """Runs the queued task at `at`; returns the hook calls and any re-queue countdowns."""
        with patch('time.time', return_value=at), patch('requests.post') as post, patch(APPLY_ASYNC) as requeue:
            post.return_value.ok = True
            post.return_value.status_code = 200
            trigger_web_deploy()
        return post.call_count, [call.kwargs['countdown'] for call in requeue.call_args_list]

    def test_a_burst_builds_once_then_one_trailing_build(self):
        with patch.dict(os.environ, HOOK):
            self.assertEqual(self.burst(NOW), [web_deploy.DEBOUNCE_SECONDS])
            self.assertEqual(self.run_task(NOW + 120), (1, []))

            # Changes right after the build: exactly one trailing build, after the 10-minute window.
            trailing = self.burst(NOW + 130)
            self.assertEqual(len(trailing), 1)
            self.assertEqual(trailing[0], web_deploy.MIN_INTERVAL_SECONDS - 10)
            self.assertEqual(self.burst(NOW + 300), [])  # still pending: rides along

            # Should it run early (a worker's clock), it waits instead of building.
            self.assertEqual(self.run_task(NOW + 400), (0, [320]))
            self.assertEqual(self.run_task(NOW + 720), (1, []))


@override_settings(CACHES=LOCMEM_CACHE)
class RebuildButtonTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(email='admin@example.com', password='x')
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(user)
        self.url = reverse('admin:radio_crestin_stations_rebuild_website')

    def test_confirm_then_post_with_csrf(self):
        with patch.dict(os.environ, HOOK), \
                patch('superapp.apps.radio_crestin.tasks.trigger_web_deploy.trigger_web_deploy.delay') as delay:
            self.assertContains(self.client.get(self.url), 'Rebuild website now')
            delay.assert_not_called()
            self.assertEqual(self.client.post(self.url).status_code, 403)
            delay.assert_not_called()
            response = self.client.post(self.url, {'csrfmiddlewaretoken': self.client.cookies['csrftoken'].value})
        self.assertEqual(response.status_code, 302)
        delay.assert_called_once_with(force=True)

    def test_says_when_not_configured(self):
        with patch.dict(os.environ, {web_deploy.HOOK_URL_ENV: ''}):
            response = self.client.get(self.url, follow=True)
        self.assertContains(response, 'not configured')
        self.assertNotContains(response, 'deploy-hook.example')

    def test_a_forced_build_skips_the_wait(self):
        web_deploy.mark_built()
        with patch.dict(os.environ, HOOK), patch('requests.post') as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            self.assertTrue(trigger_web_deploy(force=True)['success'])
        post.assert_called_once()
