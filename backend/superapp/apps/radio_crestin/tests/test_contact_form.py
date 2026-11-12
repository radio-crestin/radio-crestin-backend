import io
import os
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from ..models import ContactMessage, ContactMessageImage
from ..services import contact_images, contact_notify, contact_spam
from ..views import contact_api
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
NOTIFY = 'superapp.apps.radio_crestin.views.contact_api.notify_contact_message.delay'
URL = '/api/v1/contact/'


def image_file(name='photo.jpg', fmt='JPEG', size=(400, 300), mode='RGB', exif=None):
    buffer = io.BytesIO()
    image = Image.new(mode, size, 'red')
    image.save(buffer, format=fmt, **({'exif': exif} if exif else {}))
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


def general(**overrides):
    data = {'kind': 'general', 'email': 'Ana@Example.com', 'message': 'Hello, the app is great!', 'elapsed_ms': '9000'}
    data.update(overrides)
    return data


def station(**overrides):
    data = {
        'kind': 'station', 'email': 'ana@example.com', 'name': 'Ana', 'relation': 'listener',
        'station_name': 'Radio Speranța', 'website': 'radiosperanta.ro', 'denomination': 'baptist',
        'mission': 'Evanghelizare', 'elapsed_ms': '9000',
    }
    data.update(overrides)
    return data


def announcement(**overrides):
    data = {
        'kind': 'announcement', 'email': 'ana@example.com', 'name': 'Ana', 'about': 'general',
        'title': 'Concert de Crăciun', 'summary': 'Vă așteptăm!', 'elapsed_ms': '9000',
    }
    data.update(overrides)
    return data


@override_settings(CACHES=LOCMEM_CACHE)
class ContactTestCase(TestCase):
    def setUp(self):
        cache.clear()
        patcher = patch(NOTIFY)
        self.notify = patcher.start()
        self.addCleanup(patcher.stop)

    def send(self, data, **extra):
        return self.client.post(URL, data, **extra)

    def errors(self, data):
        response = self.send(data)
        self.assertEqual(response.status_code, 400, response.content)
        return response.json()['errors']


class GeneralMessageTests(ContactTestCase):
    def test_a_valid_message_is_stored_and_the_team_notified(self):
        response = self.send(general(source='app', platform='android', app_version='1.6.2', device_id='abc'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        message = ContactMessage.objects.get()
        self.assertEqual((message.kind, message.status, message.email), ('general', 'new', 'ana@example.com'))
        self.assertEqual((message.source, message.platform, message.app_version), ('app', 'android', '1.6.2'))
        self.assertEqual(message.subject, 'Hello, the app is great!')
        self.assertEqual(message.details, {})
        self.notify.assert_called_once_with(message.pk)

    def test_missing_and_invalid_fields_get_codes(self):
        self.assertEqual(self.errors(general(email='', message='short')), {'email': 'required', 'message': 'too_short'})
        self.assertEqual(self.errors(general(email='not-an-email')), {'email': 'invalid_email'})
        self.assertEqual(self.errors(general(message='x' * 5001)), {'message': 'too_long'})
        self.assertEqual(self.errors(general(kind='other')), {'kind': 'invalid_choice'})
        self.assertFalse(ContactMessage.objects.exists())

    def test_control_characters_are_removed(self):
        self.send(general(message='Hello\x00 there,\r\nfriends\x07!'))
        self.assertEqual(ContactMessage.objects.get().message, 'Hello there,\nfriends!')


class StationRequestTests(ContactTestCase):
    def test_answers_are_kept_and_links_get_a_scheme(self):
        self.assertEqual(self.send(station()).status_code, 201)
        message = ContactMessage.objects.get()
        self.assertEqual(message.subject, 'Radio Speranța')
        self.assertEqual(message.details['website'], 'https://radiosperanta.ro')
        self.assertEqual(message.details['denomination'], 'baptist')
        self.assertNotIn('email', message.details)

    def test_rules_across_fields(self):
        self.assertEqual(self.errors(station(website='', name='')),
                         {'name': 'required', 'listen_url': 'need_website_or_listen_url'})
        self.assertEqual(self.errors(station(relation='owner')), {'consent': 'consent_required'})
        self.assertEqual(self.errors(station(denomination='other')), {'denomination_other': 'required'})
        self.assertEqual(self.errors(station(denomination='cult')), {'denomination': 'invalid_choice'})
        self.assertEqual(self.errors(station(website='javascript:alert(1)')), {'website': 'invalid_url'})
        self.assertEqual(self.send(station(relation='owner', consent='true')).status_code, 201)


class AnnouncementRequestTests(ContactTestCase):
    def test_a_station_announcement_needs_a_listed_station(self):
        make_station('speranta')
        make_station('ascuns', disabled=True)
        self.assertEqual(self.errors(announcement(about='station')), {'station_slug': 'required'})
        self.assertEqual(self.errors(announcement(about='station', station_slug='nope')), {'station_slug': 'unknown_station'})
        self.assertEqual(self.errors(announcement(about='station', station_slug='ascuns')), {'station_slug': 'unknown_station'})
        self.assertEqual(self.send(announcement(about='station', station_slug='speranta')).status_code, 201)

    def test_dates(self):
        self.assertEqual(self.errors(announcement(starts_on='2026-12-20', ends_on='2026-12-01')), {'ends_on': 'end_before_start'})
        self.assertEqual(self.errors(announcement(starts_on='20/12/2026')), {'starts_on': 'invalid_date'})


class ImageUploadTests(ContactTestCase):
    def test_images_are_reencoded_without_metadata(self):
        exif = Image.Exif()
        exif[0x010F] = 'SecretCam'  # Make
        response = self.send(general(images=[image_file(exif=exif.tobytes()), image_file('logo.png', 'PNG', mode='RGBA')]))
        self.assertEqual(response.status_code, 201)
        stored = list(ContactMessageImage.objects.order_by('id'))
        self.assertEqual(len(stored), 2)
        self.assertTrue(stored[0].image.name.startswith('contact/') and stored[0].image.name.endswith('.jpg'))
        self.assertTrue(stored[1].image.name.endswith('.png'))
        with stored[0].image.open('rb') as handle:
            data = handle.read()
        self.assertNotIn(b'SecretCam', data)
        self.assertEqual((stored[0].width, stored[0].height), (400, 300))

    def test_big_images_are_scaled_down(self):
        self.send(general(images=[image_file(size=(3000, 1500))]))
        self.assertEqual(ContactMessageImage.objects.get().width, contact_images.MAX_SIDE)

    def test_non_images_and_other_formats_are_refused(self):
        fake = SimpleUploadedFile('photo.jpg', b'<?php echo 1; ?>', content_type='image/jpeg')
        self.assertEqual(self.errors(general(images=[fake])), {'images': 'unsupported_image'})
        self.assertEqual(self.errors(general(images=[image_file('a.gif', 'GIF')])), {'images': 'unsupported_image'})
        svg = SimpleUploadedFile('a.svg', b'<svg onload="alert(1)"/>', content_type='image/svg+xml')
        self.assertEqual(self.errors(general(images=[svg])), {'images': 'unsupported_image'})
        self.assertFalse(ContactMessage.objects.exists())

    def test_limits(self):
        self.assertEqual(self.errors(general(images=[image_file() for _ in range(4)])), {'images': 'too_many_files'})
        self.assertEqual(self.errors(station(logo=[image_file(), image_file()])), {'logo': 'too_many_files'})
        with patch.object(contact_images, 'MAX_UPLOAD_BYTES', 100):
            self.assertEqual(self.errors(general(images=[image_file()])), {'images': 'file_too_large'})
        with patch.object(contact_images, 'MAX_PIXELS', 1000):
            self.assertEqual(self.errors(general(images=[image_file()])), {'images': 'image_too_large_dimensions'})

    def test_images_are_not_decoded_for_an_invalid_form(self):
        with patch.object(contact_images, 'clean_image') as clean:
            self.errors(general(email='', images=[image_file()]))
        clean.assert_not_called()

    def test_a_body_over_the_limit_is_refused_before_parsing(self):
        with patch.object(contact_api, 'MAX_BODY_BYTES', 1000):
            response = self.send(general(images=[image_file()]))
        self.assertEqual(response.status_code, 413)


class AbuseTests(ContactTestCase):
    def test_honeypot_and_instant_submissions_look_accepted_but_are_dropped(self):
        self.assertEqual(self.send(general(confirm_url='http://spam.example')).status_code, 201)
        self.assertEqual(self.send(general(elapsed_ms='500')).status_code, 201)
        self.assertEqual(self.send(general(elapsed_ms='')).status_code, 201)
        self.assertFalse(ContactMessage.objects.exists())
        self.notify.assert_not_called()

    def test_sent_messages_are_rate_limited_per_ip_but_mistakes_are_not(self):
        for _ in range(6):
            self.assertEqual(self.send(general(email='')).status_code, 400)
        for index in range(5):
            self.assertEqual(self.send(general(email=f'p{index}@example.com')).status_code, 201)
        self.assertEqual(self.send(general(email='p9@example.com')).status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 5)

    def test_attempts_are_capped_too(self):
        for _ in range(30):
            self.send(general(email=''))
        self.assertEqual(self.send(general()).status_code, 429)

    def test_turnstile_is_required_when_configured(self):
        with patch.dict(os.environ, {contact_spam.TURNSTILE_SECRET_ENV: 'secret'}):
            self.assertEqual(self.errors(general()), {'turnstile_token': 'captcha_failed'})
            with patch.object(contact_spam.requests, 'post') as post:
                post.return_value.json.return_value = {'success': True}
                self.assertEqual(self.send(general(turnstile_token='token')).status_code, 201)
            self.assertEqual(post.call_args.kwargs['data']['secret'], 'secret')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificationTests(TestCase):
    def test_email_goes_to_the_team_with_reply_to_the_sender(self):
        message = ContactMessage.objects.create(
            kind='station', subject='Radio\nInjected: header', email='ana@example.com', name='Ana',
            details={'station_name': 'Radio', 'website': 'https://radio.ro'},
        )
        with patch.dict(os.environ, {contact_notify.RECIPIENTS_ENV: 'team@example.com, boss@example.com'}):
            self.assertTrue(contact_notify.send(message))
        email = mail.outbox[0]
        self.assertEqual(email.to, ['team@example.com', 'boss@example.com'])
        self.assertEqual(email.reply_to, ['ana@example.com'])
        self.assertNotIn('\n', email.subject)
        self.assertIn('website: https://radio.ro', email.body)
        self.assertIn(reverse('admin:radio_crestin_contactmessage_change', args=(message.pk,)), email.body)

    def test_nothing_is_sent_without_recipients(self):
        message = ContactMessage.objects.create(kind='general', email='ana@example.com')
        with patch.dict(os.environ, {contact_notify.RECIPIENTS_ENV: ''}):
            self.assertFalse(contact_notify.send(message))
        self.assertEqual(mail.outbox, [])
