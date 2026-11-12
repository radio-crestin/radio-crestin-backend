"""Builds a draft station or announcement from a contact message, for an admin to finish.

A draft station is disabled and private, so no API, app or streaming pod sees it;
a draft announcement has status Draft. Images move from private storage to the
public one only here, once an admin chose to use them.
"""
import datetime
from zoneinfo import ZoneInfo

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from ..models import (
    ActionType, Announcement, AnnouncementImage, AnnouncementStatus, ContactImageRole, ContactKind,
    ContactMessage, ContactStatus, Placement, Stations,
)

LOCAL_TIMEZONE = ZoneInfo('Europe/Bucharest')
# Romanian button labels (from Codex).
LINK_BUTTON_LABEL = 'Află mai multe'
PAGE_BUTTON_LABEL = 'Citește mai mult'


class DraftError(Exception):
    pass


def _unique_slug(model, text: str, fallback: str, max_length: int) -> str:
    base = (slugify(text) or fallback)[:max_length - 4].strip('-') or fallback
    slug, number = base, 2
    while model.objects.filter(slug=slug).exists():
        slug, number = f'{base}-{number}', number + 1
    return slug


def _copy(contact_image) -> ContentFile:
    with contact_image.image.open('rb') as source:
        return ContentFile(source.read())


def _file_name(contact_image) -> str:
    return contact_image.image.name.rsplit('/', 1)[-1]


def _mark_in_progress(message: ContactMessage, **created):
    for field, value in created.items():
        setattr(message, field, value)
    if message.status == ContactStatus.NEW:
        message.status = ContactStatus.IN_PROGRESS
    message.save(update_fields=[*created, 'status', 'updated_at'])


@transaction.atomic
def create_station(message: ContactMessage) -> Stations:
    if message.kind != ContactKind.STATION:
        raise DraftError('Only a "New station" message makes a station.')
    if message.created_station_id:
        return message.created_station
    details = message.details
    next_order = (Stations.objects.aggregate(top=Max('station_order'))['top'] or 0) + 1
    station = Stations.objects.create(
        title=details.get('station_name', message.subject),
        slug=_unique_slug(Stations, details.get('station_name', ''), 'station', 50),
        website=details.get('website') or details.get('listen_url', ''),
        stream_url=details.get('listen_url', ''),
        email=details.get('station_email', ''),
        description=details.get('description') or None,
        station_order=next_order,
        disabled=True,
        is_public=False,
    )
    logo = message.images.filter(role=ContactImageRole.LOGO).first()
    if logo:
        station.thumbnail.save(_file_name(logo), _copy(logo), save=True)
    _mark_in_progress(message, created_station=station)
    return station


def _local_datetime(iso_date: str, time: datetime.time):
    return datetime.datetime.combine(datetime.date.fromisoformat(iso_date), time, tzinfo=LOCAL_TIMEZONE)


def _page_markdown(details: dict) -> str:
    parts = [details.get('details', '')]
    if details.get('link'):
        parts.append(f"<{details['link']}>")
    return '\n\n'.join(part for part in parts if part)


def _button_fields(details: dict) -> dict:
    if details.get('details'):
        return {
            'action_type': ActionType.PAGE, 'action_label': PAGE_BUTTON_LABEL,
            'page_title': details.get('title', ''), 'page_markdown': _page_markdown(details),
        }
    if details.get('link'):
        return {'action_type': ActionType.EXTERNAL, 'action_label': LINK_BUTTON_LABEL, 'action_url': details['link']}
    return {'action_type': ActionType.NONE}


@transaction.atomic
def create_announcement(message: ContactMessage) -> Announcement:
    if message.kind != ContactKind.ANNOUNCEMENT:
        raise DraftError('Only an "Announcement request" message makes an announcement.')
    if message.created_announcement_id:
        return message.created_announcement
    details = message.details
    station = Stations.objects.filter(slug=details.get('station_slug')).first() if details.get('about') == 'station' else None
    starts_on, ends_on = details.get('starts_on'), details.get('ends_on')
    announcement = Announcement.objects.create(
        slug=_unique_slug(Announcement, details.get('title', ''), 'anunt', 120),
        status=AnnouncementStatus.DRAFT,
        title=details.get('title', message.subject),
        body_markdown=details.get('summary', ''),
        placement=Placement.STATION if station else Placement.HOME,
        starts_at=_local_datetime(starts_on, datetime.time.min) if starts_on else timezone.now(),
        ends_at=_local_datetime(ends_on, datetime.time.max) if ends_on else None,
        **_button_fields(details),
    )
    if station:
        announcement.stations.set([station])
    images = list(message.images.filter(role=ContactImageRole.IMAGE))
    if images:
        announcement.page_cover_image.save(_file_name(images[0]), _copy(images[0]), save=True)
    for image in images[1:]:
        page_image = AnnouncementImage(announcement=announcement)
        page_image.image.save(_file_name(image), _copy(image), save=True)
    _mark_in_progress(message, created_announcement=announcement)
    return announcement
