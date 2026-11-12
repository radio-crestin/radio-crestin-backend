"""The announcements clients see: serialization, the cached active list, per-request filtering."""
from datetime import datetime, timezone as dt_timezone
from typing import Optional

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import ActionType, Announcement, AnnouncementSettings, Placement, SecondaryButtonKind
from ..models.announcement_categories import text_color_on
from .announcement_targeting import Audience, TargetingRules, matches

CACHE_KEY = 'announcements:active:v1'
CACHE_SECONDS = 30


def invalidate_cache():
    cache.delete(CACHE_KEY)


def settings_payload(settings: AnnouncementSettings) -> dict:
    return {
        'rotation_mode': settings.rotation_mode,
        'autoplay_seconds': settings.autoplay_seconds,
        'max_per_load': settings.max_per_load,
    }


def iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(dt_timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _file_url(file_field) -> Optional[str]:
    return file_field.url if file_field else None


def _action_payload(action_type, url, web_target, intent_uri, fallback_url, station) -> dict:
    return {
        'type': action_type,
        'url': url or None,
        'web_target': web_target,
        'android_intent_uri': intent_uri or None,
        'fallback_url': fallback_url or None,
        'station_slug': station.slug if station else None,
    }


def _button_payload(announcement: Announcement) -> Optional[dict]:
    if announcement.action_type == ActionType.NONE:
        return None
    color = announcement.color
    return {
        'label': announcement.action_label,
        'style': announcement.button_style,
        'color': color,
        'text_color': announcement.button_text_color or text_color_on(color),
        'icon': announcement.button_icon or 'auto',
        'action': _action_payload(
            announcement.action_type, announcement.action_url, announcement.web_link_target,
            announcement.android_intent_uri, announcement.fallback_url, announcement.station,
        ),
    }


def _secondary_button_payload(announcement: Announcement) -> Optional[dict]:
    kind = announcement.secondary_kind
    if kind == SecondaryButtonKind.NONE:
        return None
    action = None
    if kind == SecondaryButtonKind.ACTION:
        action = _action_payload(
            announcement.secondary_action_type, announcement.secondary_action_url,
            announcement.secondary_web_link_target, announcement.secondary_android_intent_uri,
            announcement.secondary_fallback_url, announcement.secondary_station,
        )
    return {
        'label': announcement.secondary_label,
        'kind': kind,
        'later_days': announcement.secondary_later_days if kind == SecondaryButtonKind.LATER else None,
        'action': action,
    }


def _page_payload(announcement: Announcement) -> Optional[dict]:
    if not (announcement.page_title or announcement.page_markdown or announcement.page_cover_image):
        return None
    return {
        'title': announcement.page_title or announcement.title,
        'cover_image_url': _file_url(announcement.page_cover_image),
        'markdown': announcement.page_markdown,
    }


def _category_payload(category) -> Optional[dict]:
    if category is None:
        return None
    return {'slug': category.slug, 'name': category.name, 'color': category.color, 'text_color': category.text_color}


def station_slugs(announcement: Announcement) -> list:
    """The linked stations' slugs in station order; [] for a home announcement."""
    if announcement.placement != Placement.STATION:
        return []
    stations = sorted(announcement.stations.all(), key=lambda station: (station.station_order, station.slug))
    return [station.slug for station in stations]


def serialize(announcement: Announcement) -> dict:
    """One announcement, exactly as the API contract describes it."""
    return {
        'slug': announcement.slug,
        'priority': announcement.priority,
        'placement': announcement.placement,
        'station_slugs': station_slugs(announcement),
        'category': _category_payload(announcement.category),
        'icon': {'name': announcement.icon_name or None, 'url': _file_url(announcement.icon_image)},
        'title': announcement.title,
        'body_markdown': announcement.body_markdown,
        'button': _button_payload(announcement),
        'secondary_button': _secondary_button_payload(announcement),
        'page': _page_payload(announcement),
        'dismissible': announcement.dismissible,
        'starts_at': iso(announcement.starts_at),
        'ends_at': iso(announcement.ends_at),
        'hide_after_seconds': announcement.hide_after_seconds,
        'max_impressions': announcement.max_impressions,
    }


def rule_inputs(announcement: Announcement, picked_device_ids=()) -> dict:
    """The raw targeting lists, as TargetingRules.build takes them (JSON-safe, so cacheable)."""
    return {
        'platforms': list(announcement.platforms or []),
        'countries_include': list(announcement.countries_include or []),
        'countries_exclude': list(announcement.countries_exclude or []),
        'locales': list(announcement.locales or []),
        'device_ids': [*picked_device_ids, *(announcement.extra_device_ids or [])],
        'ip_ranges': list(announcement.ip_ranges or []),
        'min_app_version': announcement.min_app_version,
        'max_app_version': announcement.max_app_version,
    }


def rules_for(announcement: Announcement) -> TargetingRules:
    picked = announcement.target_devices.exclude(anonymous_id__isnull=True).values_list('anonymous_id', flat=True)
    return TargetingRules.build(**rule_inputs(announcement, picked))


def _load_active() -> dict:
    now = timezone.now()
    announcements = (
        Announcement.objects
        .filter(is_active=True)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .select_related('category', 'station', 'secondary_station')
        .prefetch_related('target_devices', 'stations')
        .order_by('-priority', '-starts_at', '-id')
    )
    entries = []
    for announcement in announcements:
        picked = [user.anonymous_id for user in announcement.target_devices.all() if user.anonymous_id]
        entries.append({
            'payload': serialize(announcement),
            'rules': rule_inputs(announcement, picked),
        })
    return {'settings': settings_payload(AnnouncementSettings.load()), 'entries': entries}


def active_snapshot() -> dict:
    """Active announcements not yet ended, plus settings; cached for CACHE_SECONDS."""
    snapshot = cache.get(CACHE_KEY)
    if snapshot is None:
        snapshot = _load_active()
        cache.set(CACHE_KEY, snapshot, CACHE_SECONDS)
    return snapshot


def _in_window(payload: dict, now: datetime) -> bool:
    starts_at = parse_datetime(payload['starts_at']) if payload['starts_at'] else None
    ends_at = parse_datetime(payload['ends_at']) if payload['ends_at'] else None
    return (starts_at is None or starts_at <= now) and (ends_at is None or ends_at > now)


def announcements_for(audience: Audience) -> dict:
    """The list response for one device: targeted and in its time window.

    max_per_load caps the home card only; every matching station announcement is
    returned, since clients show those per playing station.
    """
    snapshot = active_snapshot()
    now = timezone.now()
    settings = snapshot['settings']
    visible, home_count = [], 0
    for entry in snapshot['entries']:
        payload = entry['payload']
        if not _in_window(payload, now) or not matches(TargetingRules.build(**entry['rules']), audience):
            continue
        if payload['placement'] == Placement.HOME:
            if home_count >= settings['max_per_load']:
                continue
            home_count += 1
        visible.append(payload)
    return {'settings': settings, 'announcements': visible}


def live_announcement(slug: str) -> Optional[dict]:
    """One active announcement inside its time window, without targeting (push taps, shared links)."""
    now = timezone.now()
    for entry in active_snapshot()['entries']:
        if entry['payload']['slug'] == slug and _in_window(entry['payload'], now):
            return entry['payload']
    return None
