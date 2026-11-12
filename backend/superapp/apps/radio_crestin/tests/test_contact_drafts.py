import io
import datetime

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from ..models import (
    ActionType, AnnouncementStatus, ContactMessage, ContactMessageImage, ContactStatus, Placement,
    Stations,
)
from ..services import contact_drafts
from .helpers import make_station

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (64, 64), 'blue').save(buffer, format='PNG')
    return buffer.getvalue()


def attach(message, role='image'):
    image = ContactMessageImage(message=message, role=role, width=64, height=64)
    image.image.save('upload.png', ContentFile(png_bytes()), save=True)
    return image


def station_message(**details):
    return ContactMessage.objects.create(kind='station', email='ana@example.com', subject='Radio Speranța', details={
        'station_name': 'Radio Speranța', 'website': 'https://radiosperanta.ro',
        'listen_url': 'https://stream.radiosperanta.ro/live.mp3', 'description': 'Muzică creștină',
        'station_email': 'contact@radiosperanta.ro', **details,
    })


def announcement_message(**details):
    return ContactMessage.objects.create(kind='announcement', email='ana@example.com', subject='Concert', details={
        'about': 'general', 'title': 'Concert de Crăciun', 'summary': 'Vă așteptăm!', **details,
    })


@override_settings(CACHES=LOCMEM_CACHE)
class DraftStationTests(TestCase):
    def test_the_draft_is_hidden_everywhere_and_takes_the_logo(self):
        make_station('radio-speranta', station_order=7)
        message = station_message()
        attach(message, role='logo')
        station = contact_drafts.create_station(message)
        self.assertTrue(station.disabled)
        self.assertFalse(station.is_public)
        self.assertEqual(station.slug, 'radio-speranta-2')
        self.assertEqual(station.stream_url, 'https://stream.radiosperanta.ro/live.mp3')
        self.assertEqual(station.email, 'contact@radiosperanta.ro')
        self.assertEqual(station.station_order, 8)
        self.assertTrue(station.thumbnail_url)
        message.refresh_from_db()
        self.assertEqual((message.created_station, message.status), (station, ContactStatus.IN_PROGRESS))

    def test_a_second_click_returns_the_same_draft(self):
        message = station_message()
        self.assertEqual(contact_drafts.create_station(message), contact_drafts.create_station(message))
        self.assertEqual(Stations.objects.count(), 1)

    def test_only_a_station_message_makes_a_station(self):
        with self.assertRaises(contact_drafts.DraftError):
            contact_drafts.create_station(announcement_message())


@override_settings(CACHES=LOCMEM_CACHE)
class DraftAnnouncementTests(TestCase):
    def test_a_station_announcement_with_a_page_and_images(self):
        speranta = make_station('speranta')
        message = announcement_message(
            about='station', station_slug='speranta', details='Program complet', link='https://speranta.ro/concert',
            starts_on='2026-12-20', ends_on='2026-12-24',
        )
        attach(message)
        attach(message)
        announcement = contact_drafts.create_announcement(message)
        self.assertEqual(announcement.status, AnnouncementStatus.DRAFT)
        self.assertEqual(announcement.slug, 'concert-de-craciun')
        self.assertEqual(announcement.body_markdown, 'Vă așteptăm!')
        self.assertEqual(announcement.placement, Placement.STATION)
        self.assertEqual(list(announcement.stations.all()), [speranta])
        self.assertEqual(announcement.action_type, ActionType.PAGE)
        self.assertEqual(announcement.page_markdown, 'Program complet\n\n<https://speranta.ro/concert>')
        self.assertTrue(announcement.page_cover_image)
        self.assertEqual(announcement.images.count(), 1)
        self.assertEqual(announcement.starts_at.date(), datetime.date(2026, 12, 20))
        self.assertEqual(announcement.ends_at.astimezone(contact_drafts.LOCAL_TIMEZONE).date(), datetime.date(2026, 12, 24))

    def test_a_general_announcement_with_only_a_link(self):
        announcement = contact_drafts.create_announcement(announcement_message(link='https://example.com'))
        self.assertEqual(announcement.placement, Placement.HOME)
        self.assertEqual((announcement.action_type, announcement.action_url), (ActionType.EXTERNAL, 'https://example.com'))
        self.assertEqual(announcement.action_label, contact_drafts.LINK_BUTTON_LABEL)
        self.assertIsNone(announcement.ends_at)


@override_settings(CACHES=LOCMEM_CACHE)
class ContactAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(email='admin@example.com', password='x'))

    def change_url(self, message):
        return reverse('admin:radio_crestin_contactmessage_change', args=(message.pk,))

    def test_list_and_detail_pages_render_answers_escaped(self):
        message = station_message(note='<script>alert(1)</script>')
        attach(message, role='logo')
        self.assertEqual(self.client.get(reverse('admin:radio_crestin_contactmessage_changelist')).status_code, 200)
        page = self.client.get(self.change_url(message)).content.decode()
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('Create draft station', page)
        self.assertNotIn('Create draft announcement', page)
        message.refresh_from_db()
        self.assertEqual(message.status, ContactStatus.IN_PROGRESS)

    def test_the_buttons_create_drafts_and_open_them(self):
        message = station_message()
        response = self.client.get(reverse('admin:radio_crestin_contactmessage_create_draft_station', args=(message.pk,)))
        station = Stations.objects.get()
        self.assertRedirects(response, reverse('admin:radio_crestin_stations_change', args=(station.pk,)),
                             fetch_redirect_response=False)

        message = announcement_message()
        page = self.client.get(self.change_url(message)).content.decode()
        self.assertIn('Create draft announcement', page)
        response = self.client.get(reverse('admin:radio_crestin_contactmessage_create_draft_announcement', args=(message.pk,)))
        message.refresh_from_db()
        announcement = message.created_announcement
        self.assertRedirects(response, reverse('admin:radio_crestin_announcement_change', args=(announcement.pk,)),
                             fetch_redirect_response=False)

    def test_the_station_button_refuses_another_kind(self):
        message = announcement_message()
        response = self.client.get(reverse('admin:radio_crestin_contactmessage_create_draft_station', args=(message.pk,)))
        self.assertNotEqual(response.status_code, 302)
        self.assertFalse(Stations.objects.exists())
