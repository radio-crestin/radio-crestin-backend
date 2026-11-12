import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from firebase_admin import messaging

from ..models import Announcement, AnnouncementCategory, AnnouncementEvent, AppUsers
from ..services import announcement_push
from ..tasks.delete_old_announcement_events import delete_old_announcement_events
from ..tasks.send_announcement_push import send_scheduled_announcement_pushes
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CONFIGURED = {announcement_push.CREDENTIALS_ENV: '{"type": "service_account"}'}


def make_user(device_id, platform='android', token=None, **fields):
    return AppUsers.objects.create(
        anonymous_id=device_id, device_platform=platform,
        device_fcm_token=token if token is not None else f'token-{device_id}', **fields,
    )


def make_announcement(**fields):
    defaults = {
        'slug': 'concert', 'title': 'Concert', 'body_markdown': 'Live **tonight** at [19:00](https://x.ro)',
        'category': AnnouncementCategory.objects.get(slug='event'), 'action_type': 'page',
        'starts_at': timezone.now() - timedelta(minutes=5), 'status': 'active',
    }
    defaults.update(fields)
    return Announcement.objects.create(**defaults)


class FakeFcm:
    """Stands in for messaging.send_each_for_multicast; fails the tokens it's told to."""

    def __init__(self, unregistered=(), other_failures=()):
        self.unregistered, self.other_failures = set(unregistered), set(other_failures)
        self.messages = []

    def __call__(self, message, app=None):
        self.messages.append(message)
        return SimpleNamespace(responses=[self._result(token) for token in message.tokens])

    def _result(self, token):
        if token in self.unregistered:
            return SimpleNamespace(success=False, exception=messaging.UnregisteredError('gone'))
        if token in self.other_failures:
            return SimpleNamespace(success=False, exception=messaging.QuotaExceededError('slow down'))
        return SimpleNamespace(success=True, exception=None)


@override_settings(CACHES=LOCMEM_CACHE)
class ReachTests(TestCase):
    def test_breakdown_by_platform_and_missing_tokens(self):
        make_user('a1')
        make_user('a2', platform='Android')
        make_user('i1', platform='ios')
        make_user('i2', platform='ios', token='')
        make_user('a3', token='')
        make_user('w1', platform='web')
        self.assertEqual(announcement_push.reach(make_announcement()),
                         {'android': 2, 'ios': 1, 'without_token': 2, 'total': 3})

    def test_uses_the_same_targeting_as_the_card(self):
        make_user('ro-phone', device_country='RO', device_locale='ro_RO', device_app_version='1.6.2')
        make_user('de-ro-phone', device_country='DE', device_locale='ro-RO', device_app_version='1.6.2')
        make_user('de-phone', device_country='DE', device_locale='de_DE', device_app_version='1.6.2')
        make_user('old-app', device_country='DE', device_locale='ro_RO', device_app_version='1.5.0')
        make_user('ios-ro', platform='ios', device_country='DE', device_locale='ro', device_app_version='1.7')
        announcement = make_announcement(
            countries_include=['DE'], locales=['ro'], min_app_version='1.6.0', platforms=['android', 'ios', 'web_mobile'],
        )
        devices = {device.id for device in announcement_push.matching_devices(announcement)}
        self.assertEqual(devices, set(AppUsers.objects.filter(
            anonymous_id__in=['de-ro-phone', 'ios-ro']).values_list('id', flat=True)))

        announcement.platforms = ['ios']
        announcement.save()
        self.assertEqual(announcement_push.reach(announcement), {'android': 0, 'ios': 1, 'without_token': 0, 'total': 1})

    def test_web_only_announcement_reaches_no_phones(self):
        make_user('a1')
        self.assertEqual(announcement_push.reach(make_announcement(platforms=['web_desktop']))['total'], 0)


@override_settings(CACHES=LOCMEM_CACHE)
class SendTests(TestCase):
    def send(self, announcement, fcm):
        with patch.dict(os.environ, CONFIGURED), \
                patch.object(announcement_push, '_firebase_app', return_value=object()), \
                patch.object(messaging, 'send_each_for_multicast', side_effect=fcm), \
                patch.object(announcement_push, 'track_event') as track_event:
            result = announcement_push.send(announcement)
        return result, track_event

    def test_bad_credentials_never_echo_the_key(self):
        secret = '{"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----SECRET"}'
        with patch.dict(os.environ, {announcement_push.CREDENTIALS_ENV: secret}):
            with self.assertRaises(RuntimeError) as raised:
                announcement_push._firebase_app()
        self.assertNotIn('SECRET', str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)

    def test_not_configured(self):
        with patch.dict(os.environ, {announcement_push.CREDENTIALS_ENV: ''}):
            self.assertFalse(announcement_push.is_configured())
            with self.assertRaises(RuntimeError):
                announcement_push.send(make_announcement())

    def test_payload(self):
        make_user('a1')
        fcm = FakeFcm()
        self.send(make_announcement(push_title='', push_body=''), fcm)
        message = fcm.messages[0]
        self.assertEqual(message.notification.title, 'Concert')
        self.assertEqual(message.notification.body, 'Live tonight at 19:00')
        self.assertIsNone(message.notification.image)
        self.assertEqual(message.data, {'type': 'announcement', 'slug': 'concert'})
        self.assertEqual(message.android.notification.channel_id, 'announcements')

    def test_station_announcement_carries_its_first_station(self):
        make_user('a1')
        announcement = make_announcement(placement='station')
        announcement.stations.add(make_station('vocea', station_order=1.0), make_station('elim', station_order=2.0))
        fcm = FakeFcm()
        self.send(announcement, fcm)
        self.assertEqual(fcm.messages[0].data, {'type': 'announcement', 'slug': 'concert', 'station_slug': 'vocea'})

    def test_test_send_reaches_only_the_test_devices_and_records_nothing(self):
        mine = make_user('mine', platform='ios')
        make_user('someone-else')
        announcement = make_announcement()
        announcement.test_devices.add(mine)
        fcm = FakeFcm()
        with patch.dict(os.environ, CONFIGURED), \
                patch.object(announcement_push, '_firebase_app', return_value=object()), \
                patch.object(messaging, 'send_each_for_multicast', side_effect=fcm), \
                patch.object(announcement_push, 'track_event') as track_event:
            result = announcement_push.send_test(announcement)
        self.assertEqual(fcm.messages[0].tokens, ['token-mine'])
        self.assertEqual(result['ios'], 1)
        track_event.assert_not_called()
        announcement.refresh_from_db()
        self.assertEqual((announcement.push_sent_at, announcement.push_sent_count), (None, 0))

    def test_batches_of_500_counts_cleanup_and_posthog(self):
        AppUsers.objects.bulk_create([
            AppUsers(anonymous_id=f'a{index}', device_platform='android', device_fcm_token=f'token-a{index}')
            for index in range(600)
        ])
        make_user('i1', platform='ios')
        make_user('dup', token='token-a1')  # same token as a1: sent once
        fcm = FakeFcm(unregistered={'token-a5', 'token-i1'}, other_failures={'token-a7'})
        announcement = make_announcement(push_title='Tonight', push_body='At 19:00')

        result, track_event = self.send(announcement, fcm)

        self.assertEqual([len(message.tokens) for message in fcm.messages], [500, 101])
        self.assertEqual(fcm.messages[0].notification.title, 'Tonight')
        self.assertEqual(result, {'sent': 598, 'android': 598, 'ios': 0, 'failed': 3, 'cleared_tokens': 2})
        self.assertIsNone(AppUsers.objects.get(anonymous_id='a5').device_fcm_token)
        self.assertIsNone(AppUsers.objects.get(anonymous_id='i1').device_fcm_token)
        self.assertEqual(AppUsers.objects.get(anonymous_id='a7').device_fcm_token, 'token-a7')

        announcement.refresh_from_db()
        self.assertEqual(announcement.push_sent_count, 598)
        self.assertIsNotNone(announcement.push_sent_at)

        distinct_id, event, properties = track_event.call_args.args
        self.assertEqual(event, 'announcement_push_sent')
        self.assertEqual(properties['announcement_slug'], 'concert')
        self.assertEqual(properties['announcement_category'], 'event')
        self.assertEqual(properties['action_type'], 'page')
        self.assertEqual(properties['sent_count'], 598)


@override_settings(CACHES=LOCMEM_CACHE)
class ScheduledPushTests(TestCase):
    def run_beat(self):
        with patch.dict(os.environ, CONFIGURED), \
                patch('superapp.apps.radio_crestin.tasks.send_announcement_push.send_announcement_push.delay') as delay:
            result = send_scheduled_announcement_pushes()
        return result, delay

    def test_sends_confirmed_started_announcements_once(self):
        due = make_announcement(slug='due', push_enabled=True, push_schedule='at_start',
                                push_confirmed_at=timezone.now())
        make_announcement(slug='unconfirmed', push_enabled=True, push_schedule='at_start')
        make_announcement(slug='future', push_enabled=True, push_schedule='at_start',
                          push_confirmed_at=timezone.now(), starts_at=timezone.now() + timedelta(hours=1))
        make_announcement(slug='manual', push_enabled=True, push_schedule='manual', push_confirmed_at=timezone.now())

        result, delay = self.run_beat()
        self.assertEqual(result['queued'], 1)
        delay.assert_called_once_with(due.pk)

        result, delay = self.run_beat()
        self.assertEqual(result['queued'], 0)
        delay.assert_not_called()

    def test_does_nothing_when_push_is_not_configured(self):
        make_announcement(push_enabled=True, push_schedule='at_start', push_confirmed_at=timezone.now())
        with patch.dict(os.environ, {announcement_push.CREDENTIALS_ENV: ''}):
            self.assertEqual(send_scheduled_announcement_pushes()['queued'], 0)
        self.assertIsNone(Announcement.objects.get(slug='concert').push_sent_at)


@override_settings(CACHES=LOCMEM_CACHE)
class EventRetentionTests(TestCase):
    def test_deletes_events_older_than_180_days(self):
        announcement = make_announcement()
        old = AnnouncementEvent.objects.create(announcement=announcement, type='impression')
        recent = AnnouncementEvent.objects.create(announcement=announcement, type='impression')
        AnnouncementEvent.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=181))
        AnnouncementEvent.objects.filter(pk=recent.pk).update(created_at=timezone.now() - timedelta(days=179))

        self.assertEqual(delete_old_announcement_events()['deleted_count'], 1)
        self.assertEqual(list(AnnouncementEvent.objects.values_list('pk', flat=True)), [recent.pk])
