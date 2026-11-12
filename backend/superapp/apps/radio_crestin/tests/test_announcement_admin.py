import os
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..forms.announcement_admin import AnnouncementAdminForm
from ..models import Announcement, AnnouncementCategory, AnnouncementEvent, AnnouncementSettings, AppUsers
from ..services import announcement_push
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CONFIGURED = {announcement_push.CREDENTIALS_ENV: '{"type": "service_account"}'}
NOT_CONFIGURED = {announcement_push.CREDENTIALS_ENV: ''}


def form_data(**overrides):
    data = {
        'slug': 'concert', 'title': 'Concert', 'body_markdown': 'Live **tonight**.', 'icon_name': 'calendar',
        'status': 'active',
        'placement': 'home', 'action_type': 'none', 'web_link_target': 'new_tab', 'button_style': 'filled',
        'button_icon': 'auto', 'dismissible': 'on',
        'starts_at': '2026-11-12 10:00:00', 'push_schedule': 'manual',
    }
    data.update(overrides)
    return data


class AnnouncementFormTests(TestCase):
    def errors(self, **overrides):
        form = AnnouncementAdminForm(data=form_data(**overrides))
        form.is_valid()
        return form.errors

    def test_minimal_announcement_is_valid(self):
        self.assertEqual(self.errors(), {})

    def test_list_fields_are_split_normalized_and_validated(self):
        form = AnnouncementAdminForm(data=form_data(
            countries_include='ro, md\nDE', countries_exclude='md md', locales='ro\nen_US',
            platforms=['android', 'web_mobile'],
        ))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['countries_include'], ['RO', 'MD', 'DE'])
        self.assertEqual(form.cleaned_data['countries_exclude'], ['MD'])
        self.assertEqual(form.cleaned_data['locales'], ['ro', 'en_US'])
        self.assertEqual(form.cleaned_data['platforms'], ['android', 'web_mobile'])

        self.assertIn('countries_include', self.errors(countries_include='Romania'))
        self.assertIn('locales', self.errors(locales='ro!'))

    def test_button_rules(self):
        self.assertIn('action_label', self.errors(action_type='external', action_url='https://x.ro'))
        self.assertIn('action_url', self.errors(action_type='external', action_label='Go'))
        self.assertEqual(self.errors(action_type='external', action_url='https://x.ro', button_style='hidden'), {})
        self.assertIn('fallback_url', self.errors(
            action_type='android_intent', action_label='Open', android_intent_uri='intent://x#Intent;end'))
        self.assertIn('station', self.errors(action_type='station', action_label='Listen'))
        self.assertIn('page_markdown', self.errors(action_type='page', action_label='Read'))

    def test_links_must_use_safe_schemes(self):
        external = {'action_type': 'external', 'action_label': 'Go'}
        for url in ('https://x.ro', 'http://x.ro/a?b=1', 'mailto:radio@x.ro', 'tel:+40700000000'):
            self.assertEqual(self.errors(action_url=url, **external), {}, url)
        for url in ('javascript:alert(1)', 'JavaScript:alert(1)', 'data:text/html,x', 'vbscript:x',
                    'file:///etc/passwd', 'ftp://x.ro', 'mailto:', 'x.ro'):
            self.assertIn('action_url', self.errors(action_url=url, **external), url)

        intent = {'action_type': 'android_intent', 'action_label': 'Open'}
        self.assertEqual(self.errors(android_intent_uri='intent://x#Intent;end', fallback_url='https://x.ro', **intent), {})
        self.assertIn('android_intent_uri', self.errors(
            android_intent_uri='javascript:x', fallback_url='https://x.ro', **intent))
        self.assertIn('fallback_url', self.errors(
            android_intent_uri='intent://x#Intent;end', fallback_url='mailto:a@b.ro', **intent))

    def test_there_is_no_second_button(self):
        form = AnnouncementAdminForm(data=form_data())
        for name in ('secondary_kind', 'secondary_label', 'secondary_later_days', 'secondary_action_type'):
            self.assertNotIn(name, form.fields)

    def test_slugs_are_strict(self):
        for slug in ('Concert', 'concert_2026', 'concert 2026', 'a' * 101, 'ciné'):
            self.assertIn('slug', self.errors(slug=slug), slug)
        self.assertEqual(self.errors(slug='concert-craciun-2026'), {})

    def test_colors_are_optional_but_must_be_hex(self):
        self.assertEqual(self.errors(button_color='', button_text_color=''), {})
        self.assertIn('button_color', self.errors(button_color='red'))

    def test_description_is_optional_with_a_labelled_button(self):
        button = {'action_type': 'external', 'action_url': 'https://chat.whatsapp.com/x', 'body_markdown': ''}
        self.assertEqual(self.errors(action_label='Primește-l zilnic pe WhatsApp', **button), {})
        self.assertIn('body_markdown', self.errors(action_label='', button_style='hidden', **button))
        self.assertIn('body_markdown', self.errors(body_markdown='   '))
        self.assertEqual(self.errors(body_markdown='Text.'), {})

    def test_the_seeded_whatsapp_announcement_saves_in_the_admin_form(self):
        from django.forms.models import model_to_dict
        whatsapp = Announcement.objects.get(slug='whatsapp-versetul-zilei')
        data = {key: value for key, value in model_to_dict(whatsapp).items() if value is not None}
        data['starts_at'] = whatsapp.starts_at.strftime('%Y-%m-%d %H:%M:%S')
        form = AnnouncementAdminForm(data=data, instance=whatsapp)
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_rules(self):
        self.assertIn('body_markdown', self.errors(body_markdown=''))  # neither a body nor a button
        self.assertIn('icon_name', self.errors(icon_name=''))
        self.assertIn('slug', self.errors(slug='events'))
        self.assertIn('stations', self.errors(placement='station'))
        self.assertIn('ends_at', self.errors(ends_at='2026-11-11 10:00:00'))


@override_settings(CACHES=LOCMEM_CACHE)
class AnnouncementAdminPagesTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(email='admin@example.com', password='x')
        self.client.force_login(self.admin_user)
        self.announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')

    def test_list_shows_unique_numbers(self):
        for device_id in ('a', 'a', 'b'):
            AnnouncementEvent.objects.create(announcement=self.announcement, type='impression', device_id=device_id)
        AnnouncementEvent.objects.create(announcement=self.announcement, type='clicked', device_id='a')
        response = self.client.get(reverse('admin:radio_crestin_announcement_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '50.0%')

    def test_add_and_change_pages_render(self):
        with patch.dict(os.environ, NOT_CONFIGURED):
            self.assertEqual(self.client.get(reverse('admin:radio_crestin_announcement_add')).status_code, 200)
            response = self.client.get(reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Push is not configured')
        self.assertContains(response, 'data-markdown-preview')
        self.assertNotContains(response, 'secondary_kind')
        self.assertContains(response, 'Send push notification')

    def test_change_page_shows_reach_when_configured(self):
        AppUsers.objects.create(anonymous_id='p1', device_platform='android', device_fcm_token='t1')
        with patch.dict(os.environ, CONFIGURED):
            response = self.client.get(reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,)))
        self.assertContains(response, 'Android 1 · iPhone 0 · without token 0')

    def test_saving_through_the_admin_form(self):
        station = make_station('radio-elim')
        data = form_data(
            slug='inside-elim', title='Pray with us', placement='station', stations=[station.pk],
            platforms=['android', 'ios'], countries_include='ro md', locales='ro',
            category=AnnouncementCategory.objects.get(slug='prayer').pk,
            action_type='station', action_label='Listen now', station=station.pk, button_style='outline',
            **{'images-TOTAL_FORMS': '0', 'images-INITIAL_FORMS': '0',
               'images-MIN_NUM_FORMS': '0', 'images-MAX_NUM_FORMS': '1000'},
        )
        del data['starts_at']
        data.update({'starts_at_0': '2026-11-12', 'starts_at_1': '10:00:00'})
        response = self.client.post(reverse('admin:radio_crestin_announcement_add'), data)
        self.assertEqual(response.status_code, 302, response.content.decode()[:3000])
        saved = Announcement.objects.get(slug='inside-elim')
        self.assertEqual(saved.platforms, ['android', 'ios'])
        self.assertEqual(saved.countries_include, ['RO', 'MD'])
        self.assertEqual(list(saved.stations.values_list('slug', flat=True)), ['radio-elim'])

    def test_preview_links_and_token_rotation(self):
        settings = AnnouncementSettings.load()
        response = self.client.get(reverse('admin:radio_crestin_announcement_change', args=(self.announcement.pk,)))
        self.assertContains(response, settings.website_preview_url)
        self.assertContains(response, settings.app_preview_url)

    def test_rotating_the_token_needs_a_post_with_csrf(self):
        settings = AnnouncementSettings.load()
        old_token = settings.preview_token
        url = reverse('admin:radio_crestin_announcementsettings_rotate_preview_token', args=(settings.pk,))
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin_user)

        confirmation = csrf_client.get(url)
        self.assertContains(confirmation, 'Rotate preview token')
        settings.refresh_from_db()
        self.assertEqual(settings.preview_token, old_token)

        self.assertEqual(csrf_client.post(url, {'confirm': 'yes'}).status_code, 403)
        settings.refresh_from_db()
        self.assertEqual(settings.preview_token, old_token)

        csrf_client.post(url, {'confirm': 'yes', 'csrfmiddlewaretoken': csrf_client.cookies['csrftoken'].value})
        settings.refresh_from_db()
        self.assertNotEqual(settings.preview_token, old_token)

    def test_category_and_settings_pages_render(self):
        for name in ('announcementcategory', 'announcementsettings'):
            response = self.client.get(reverse(f'admin:radio_crestin_{name}_changelist'))
            self.assertEqual(response.status_code, 200, name)

    def test_test_device_picker_searches_app_users(self):
        AppUsers.objects.create(anonymous_id='my-phone', device_model='Pixel 8', device_platform='android',
                                device_app_version='1.6.2')
        response = self.client.get(reverse('admin:autocomplete'), {
            'app_label': 'radio_crestin', 'model_name': 'announcement', 'field_name': 'test_devices', 'term': 'pixel',
        })
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertIn('Pixel 8 · android · v1.6.2', results[0]['text'])


@override_settings(CACHES=LOCMEM_CACHE)
class SendPushActionTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(email='admin@example.com', password='x')
        self.client.force_login(self.admin_user)
        self.announcement = Announcement.objects.get(slug='whatsapp-versetul-zilei')
        self.url = reverse('admin:radio_crestin_announcement_send_push_notification', args=(self.announcement.pk,))
        AppUsers.objects.create(anonymous_id='a1', device_platform='android', device_fcm_token='t1')
        AppUsers.objects.create(anonymous_id='i1', device_platform='ios', device_fcm_token='t2')
        AppUsers.objects.create(anonymous_id='i2', device_platform='ios')

    def test_not_configured_goes_back_with_a_message(self):
        with patch.dict(os.environ, NOT_CONFIGURED):
            response = self.client.get(self.url, follow=True)
        self.assertContains(response, 'Push is not configured')

    def test_confirmation_shows_the_reach_and_sends_nothing(self):
        with patch.dict(os.environ, CONFIGURED), \
                patch('superapp.apps.radio_crestin.tasks.send_announcement_push.send_announcement_push.delay') as delay:
            response = self.client.get(self.url)
        self.assertContains(response, 'to 2 phones?')
        self.assertContains(response, 'Android 1 · iPhone 1 · 1 matching devices have no push token')
        delay.assert_not_called()

    def test_confirming_queues_the_send(self):
        with patch.dict(os.environ, CONFIGURED), \
                patch('superapp.apps.radio_crestin.tasks.send_announcement_push.send_announcement_push.delay') as delay:
            response = self.client.post(self.url, {'confirm': 'yes'})
        self.assertEqual(response.status_code, 302)
        delay.assert_called_once_with(self.announcement.pk)
        self.announcement.refresh_from_db()
        self.assertTrue(self.announcement.push_enabled)
        self.assertIsNotNone(self.announcement.push_confirmed_at)

    def test_test_notification_goes_to_the_picked_devices_only(self):
        mine = AppUsers.objects.get(anonymous_id='i1')
        self.announcement.test_devices.add(mine)
        test_url = reverse('admin:radio_crestin_announcement_send_test_notification', args=(self.announcement.pk,))
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin_user)
        with patch.dict(os.environ, CONFIGURED), \
                patch.object(announcement_push, '_deliver', return_value={'sent': 1, 'failed': 0}) as deliver:
            confirmation = csrf_client.get(test_url)
            self.assertContains(confirmation, str(mine))
            deliver.assert_not_called()
            self.assertEqual(csrf_client.post(test_url, {'confirm': 'yes'}).status_code, 403)
            deliver.assert_not_called()
            response = csrf_client.post(test_url, {
                'confirm': 'yes', 'csrfmiddlewaretoken': csrf_client.cookies['csrftoken'].value,
            }, follow=True)
        self.assertContains(response, 'Test notification sent to 1 device(s)')
        devices = list(deliver.call_args.args[1])
        self.assertEqual([device.token for device in devices], ['t2'])
        self.announcement.refresh_from_db()
        self.assertIsNone(self.announcement.push_sent_at)

    def test_test_notification_needs_picked_devices(self):
        test_url = reverse('admin:radio_crestin_announcement_send_test_notification', args=(self.announcement.pk,))
        with patch.dict(os.environ, CONFIGURED):
            response = self.client.get(test_url, follow=True)
        self.assertContains(response, 'Pick the test devices')

    def test_confirming_a_future_start_time_waits_for_the_beat(self):
        Announcement.objects.filter(pk=self.announcement.pk).update(
            push_schedule='at_start', starts_at=timezone.now() + timedelta(days=1))
        with patch.dict(os.environ, CONFIGURED), \
                patch('superapp.apps.radio_crestin.tasks.send_announcement_push.send_announcement_push.delay') as delay:
            self.assertContains(self.client.get(self.url), 'sent automatically at the start time')
            self.client.post(self.url, {'confirm': 'yes'})
        delay.assert_not_called()
        self.announcement.refresh_from_db()
        self.assertIsNotNone(self.announcement.push_confirmed_at)
        self.assertIsNone(self.announcement.push_sent_at)


class AppUsersLabelTests(TestCase):
    def test_device_details_in_the_label(self):
        user = AppUsers(anonymous_id='abc', device_model='Pixel 8', device_platform='android', device_app_version='1.6.2')
        self.assertEqual(str(user), 'Pixel 8 · android · v1.6.2 (abc)')
        self.assertEqual(str(AppUsers(anonymous_id='abc')), 'App User abc')
