"""Push notifications for announcements, sent through firebase-admin to the matching AppUsers."""
import json
import logging
import os
import re
from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from superapp.apps.posthog_error_tracking.utils import track_event
from ..models import Announcement, AppUsers
from .announcement_feed import rules_for, station_slugs
from .announcement_targeting import APP_PLATFORMS, Audience, TargetingRules, matches

logger = logging.getLogger(__name__)

CREDENTIALS_ENV = 'FIREBASE_SERVICE_ACCOUNT_JSON'
FIREBASE_APP_NAME = 'radio-crestin-announcements'
ANDROID_CHANNEL_ID = 'announcements'
BATCH_SIZE = 500
POSTHOG_DISTINCT_ID = 'radio-crestin-backend'


@dataclass(frozen=True)
class Device:
    id: int
    platform: str
    token: str


def is_configured() -> bool:
    return bool(os.environ.get(CREDENTIALS_ENV, '').strip())


def _firebase_app():
    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app(FIREBASE_APP_NAME)
    except ValueError:
        service_account = json.loads(os.environ[CREDENTIALS_ENV])
        return firebase_admin.initialize_app(credentials.Certificate(service_account), name=FIREBASE_APP_NAME)


# ---------------------------------------------------------------- audience

def _locale_filter(locales) -> Q:
    """Rows whose locale could match one of the rules; the exact check is `matches`."""
    condition = Q()
    for rule in locales:
        underscored = rule.replace('-', '_')
        condition |= (
            Q(device_locale__iexact=rule) | Q(device_locale__iexact=underscored)
            | Q(device_locale__istartswith=f'{rule}-') | Q(device_locale__istartswith=f'{underscored}_')
        )
    return condition


def _candidate_users(rules: TargetingRules):
    """A database pre-filter: never drops a row that `matches` would accept."""
    platforms = [platform for platform in APP_PLATFORMS if not rules.platforms or platform in rules.platforms]
    if not platforms:
        return AppUsers.objects.none()
    users = AppUsers.objects.filter(anonymous_id__isnull=False)
    platform_filter = Q()
    for platform in platforms:
        platform_filter |= Q(device_platform__iexact=platform)
    users = users.filter(platform_filter)
    if rules.countries_include:
        users = users.filter(device_country__in=rules.countries_include)
    if rules.countries_exclude:
        users = users.exclude(device_country__in=rules.countries_exclude)
    if rules.device_ids:
        users = users.filter(anonymous_id__in=rules.device_ids)
    if rules.locales:
        users = users.filter(_locale_filter(rules.locales))
    return users


def matching_devices(announcement: Announcement):
    """Every app device the announcement targets, with its push token ('' when it has none)."""
    rules = rules_for(announcement)
    rows = _candidate_users(rules).values_list(
        'id', 'device_platform', 'device_country', 'device_locale', 'anonymous_id',
        'device_last_ip', 'device_app_version', 'device_fcm_token',
    )
    for user_id, platform, country, locale, device_id, ip, app_version, token in rows.iterator(chunk_size=2000):
        audience = Audience(
            platform=(platform or '').lower(), country=country or '', locale=locale or '',
            device_id=device_id or '', ip=ip or '', app_version=app_version or '',
        )
        if matches(rules, audience):
            yield Device(id=user_id, platform=audience.platform, token=(token or '').strip())


def reach(announcement: Announcement) -> dict:
    """How many phones a send would reach, per platform, and how many matching devices have no token."""
    counts = {'android': 0, 'ios': 0, 'without_token': 0}
    for device in matching_devices(announcement):
        counts[device.platform if device.token else 'without_token'] += 1
    counts['total'] = counts['android'] + counts['ios']
    return counts


# ---------------------------------------------------------------- message

def markdown_to_plain_text(markdown: str) -> str:
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', markdown or '')
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*_`#>]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def notification_title(announcement: Announcement) -> str:
    return announcement.push_title or announcement.title


def notification_body(announcement: Announcement) -> str:
    return announcement.push_body or markdown_to_plain_text(announcement.body_markdown)


def _image_url(announcement: Announcement):
    url = announcement.push_image.url if announcement.push_image else ''
    return url if url.startswith('https://') else None


def push_data(announcement: Announcement) -> dict:
    data = {'type': 'announcement', 'slug': announcement.slug}
    linked_stations = station_slugs(announcement)
    if linked_stations:
        data['station_slug'] = linked_stations[0]
    return data


def build_message(announcement: Announcement, tokens):
    from firebase_admin import messaging

    image = _image_url(announcement)
    return messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(
            title=notification_title(announcement), body=notification_body(announcement), image=image,
        ),
        data=push_data(announcement),
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(channel_id=ANDROID_CHANNEL_ID),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(aps=messaging.Aps(sound='default', mutable_content=bool(image))),
        ),
    )


# ---------------------------------------------------------------- sending

def _batches(items, size=BATCH_SIZE):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def send(announcement: Announcement) -> dict:
    """Sends the notification to every matching device with a token; returns the counts."""
    from firebase_admin import messaging

    if not is_configured():
        raise RuntimeError(f'Push is not configured: {CREDENTIALS_ENV} is missing.')

    # One message per token, even when several rows share it.
    devices = list({device.token: device for device in matching_devices(announcement) if device.token}.values())
    app = _firebase_app()
    sent = {'android': 0, 'ios': 0}
    failed = 0
    unregistered_tokens = []

    for batch in _batches(devices):
        response = messaging.send_each_for_multicast(build_message(announcement, [d.token for d in batch]), app=app)
        for device, result in zip(batch, response.responses):
            if result.success:
                sent[device.platform] += 1
                continue
            failed += 1
            if isinstance(result.exception, messaging.UnregisteredError):
                unregistered_tokens.append(device.token)

    if unregistered_tokens:
        AppUsers.objects.filter(device_fcm_token__in=unregistered_tokens).update(device_fcm_token=None)

    result = {
        'sent': sent['android'] + sent['ios'],
        'android': sent['android'],
        'ios': sent['ios'],
        'failed': failed,
        'cleared_tokens': len(unregistered_tokens),
    }
    Announcement.objects.filter(pk=announcement.pk).update(push_sent_at=timezone.now(), push_sent_count=result['sent'])
    _capture_sent(announcement, result)
    logger.info('Announcement %s push sent: %s', announcement.slug, result)
    return result


def _capture_sent(announcement: Announcement, result: dict):
    track_event(POSTHOG_DISTINCT_ID, 'announcement_push_sent', {
        'announcement_slug': announcement.slug,
        'announcement_category': announcement.category.slug if announcement.category_id else None,
        'action_type': announcement.action_type,
        'platform': 'server',
        'sent_count': result['sent'],
        'android_count': result['android'],
        'ios_count': result['ios'],
        'failed_count': result['failed'],
        'cleared_tokens': result['cleared_tokens'],
        '$process_person_profile': False,
    })
