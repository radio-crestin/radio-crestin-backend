"""The announcements clients get: one list for everyone (cacheable by Cloudflare), filtered on the client.

Each item carries its `filters`; the website and the apps decide on the device
whether it applies. Bodies are kept in the cache with an ETag and dropped by the
signals in signals/announcements.py whenever something they serve changes.
"""
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Callable, Optional

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from ..models import (
    ActionType, Announcement, AnnouncementSettings, AnnouncementStatus, Placement,
)
from ..models.announcement_categories import text_color_on
from ..models.announcement_validators import PUBLIC_SLUG_PATTERN
from . import announcement_html
from .announcement_targeting import TargetingRules

UPCOMING_WINDOW = timedelta(days=7)
CACHE_SECONDS = 300
GENERATION_KEY = 'announcements:generation'
PUBLIC_STATUSES = (AnnouncementStatus.ACTIVE,)
PREVIEW_STATUSES = (AnnouncementStatus.ACTIVE, AnnouncementStatus.PREVIEW)
PUBLIC_SLUG_RE = re.compile(PUBLIC_SLUG_PATTERN)
STATION_SLUG_RE = re.compile(r'^[-a-zA-Z0-9_]+$')  # Django's SlugField alphabet

AbsoluteUrl = Callable[[str], str]


@dataclass(frozen=True)
class RenderedResponse:
    body: bytes
    etag: str


# ---------------------------------------------------------------- serialization

def iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(dt_timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _compact(data: dict) -> dict:
    """Drops absent optional values, so the payload stays small."""
    return {key: value for key, value in data.items() if value is not None}


def _image_url(file_field, absolute_url: AbsoluteUrl) -> Optional[str]:
    if not file_field:
        return None
    url = absolute_url(file_field.url)
    return url if url.lower().startswith(('https://', 'http://')) else None


def _action_payload(action_type, url, web_target, intent_uri, fallback_url, station, form=None) -> dict:
    return _compact({
        'type': action_type,
        'url': url or None,
        'web_target': web_target if action_type in (ActionType.EXTERNAL, ActionType.IN_APP_BROWSER) else None,
        'android_intent_uri': intent_uri or None,
        'fallback_url': fallback_url or None,
        'station_slug': _station_slug(station),
        'form_slug': form.slug if form and is_public_slug(form.slug) else None,
    })


def _button_payload(announcement: Announcement) -> Optional[dict]:
    if announcement.action_type == ActionType.NONE:
        return None
    # No color set: the key is left out and each client uses its own theme.
    color = announcement.button_color or None
    text_color = announcement.button_text_color or (text_color_on(color) if color else None)
    return _compact({
        'label': announcement.action_label,
        'style': announcement.button_style,
        'color': color,
        'text_color': text_color,
        'icon': announcement.button_icon or 'auto',
        'action': _action_payload(
            announcement.action_type, announcement.action_url, announcement.web_link_target,
            announcement.android_intent_uri, announcement.fallback_url, announcement.station, announcement.form,
        ),
    })


def _page_payload(announcement: Announcement, absolute_url: AbsoluteUrl, with_body: bool) -> Optional[dict]:
    if not (announcement.page_title or announcement.page_markdown or announcement.page_cover_image):
        return None
    page = {
        'title': announcement.page_title or announcement.title,
        'cover_image_url': _image_url(announcement.page_cover_image, absolute_url),
    }
    if with_body:
        page['markdown'] = announcement.page_markdown
        page['html'] = announcement_html.page_html(announcement.page_markdown)
    return _compact(page)


def is_public_slug(slug: str) -> bool:
    return bool(PUBLIC_SLUG_RE.match(slug or ''))


def _station_slug(station) -> Optional[str]:
    return station.slug if station and STATION_SLUG_RE.match(station.slug or '') else None


def _category_payload(category) -> Optional[dict]:
    if category is None or not is_public_slug(category.slug):
        return None
    return _compact({
        'slug': category.slug, 'name': category.name,
        'color': category.color or None, 'text_color': category.text_color,
    })


def filters_payload(announcement: Announcement) -> dict:
    return {
        'platforms': list(announcement.platforms or []),
        'countries_include': list(announcement.countries_include or []),
        'countries_exclude': list(announcement.countries_exclude or []),
        'locales': list(announcement.locales or []),
        'min_app_version': announcement.min_app_version or None,
        'max_app_version': announcement.max_app_version or None,
    }


def station_slugs(announcement: Announcement) -> list:
    """The linked stations' slugs in station order; [] for a home announcement."""
    if announcement.placement != Placement.STATION:
        return []
    stations = sorted(announcement.stations.all(), key=lambda station: (station.station_order, station.slug))
    return [slug for slug in map(_station_slug, stations) if slug]


def serialize(announcement: Announcement, absolute_url: AbsoluteUrl = lambda url: url, *,
              with_page_body: bool = False) -> dict:
    """One announcement as the API sends it; the single endpoint also sends the page body."""
    return _compact({
        'slug': announcement.slug,
        'priority': announcement.priority,
        'placement': announcement.placement,
        'station_slugs': station_slugs(announcement),
        'category': _category_payload(announcement.category),
        'icon': _compact({
            'name': announcement.icon_name or None,
            'url': _image_url(announcement.icon_image, absolute_url),
        }),
        'title': announcement.title,
        'body_markdown': announcement.body_markdown,
        'body_html': announcement_html.body_html(announcement.body_markdown),
        'button': _button_payload(announcement),
        'page': _page_payload(announcement, absolute_url, with_page_body),
        'dismissible': announcement.dismissible,
        'starts_at': iso(announcement.starts_at),
        'ends_at': iso(announcement.ends_at),
        'hide_after_seconds': announcement.hide_after_seconds,
        'max_impressions': announcement.max_impressions,
        'filters': filters_payload(announcement),
    })


def settings_payload(settings: AnnouncementSettings) -> dict:
    return {
        'rotation_mode': settings.rotation_mode,
        'max_per_load': settings.max_per_load,
    }


def rules_for(announcement: Announcement) -> TargetingRules:
    """The filters as rules, for push sending (the server applies them there)."""
    return TargetingRules.build(
        platforms=announcement.platforms,
        countries_include=announcement.countries_include,
        countries_exclude=announcement.countries_exclude,
        locales=announcement.locales,
        min_app_version=announcement.min_app_version,
        max_app_version=announcement.max_app_version,
    )


# ---------------------------------------------------------------- queries

def _listed(statuses, now: datetime):
    """Not ended, and started or starting within UPCOMING_WINDOW (clients switch them on at starts_at)."""
    return (
        Announcement.objects
        .filter(status__in=statuses, starts_at__lte=now + UPCOMING_WINDOW)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .select_related('category', 'station', 'form')
        .prefetch_related('stations')
        .order_by('-priority', '-starts_at', '-id')
    )


def _live(statuses, slug: str, now: datetime) -> Optional[Announcement]:
    """One announcement inside its time window (push taps, #anunt/<slug> links)."""
    return (
        Announcement.objects
        .filter(slug=slug, status__in=statuses, starts_at__lte=now)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .select_related('category', 'station', 'form')
        .prefetch_related('stations')
        .first()
    )


def list_payload(absolute_url: AbsoluteUrl, statuses=PUBLIC_STATUSES) -> dict:
    now = timezone.now()
    return {
        'settings': settings_payload(AnnouncementSettings.load()),
        # The model validates slugs; anything else (older rows) is never sent.
        'announcements': [
            serialize(announcement, absolute_url) for announcement in _listed(statuses, now)
            if is_public_slug(announcement.slug)
        ],
    }


def detail_payload(slug: str, absolute_url: AbsoluteUrl, statuses=PUBLIC_STATUSES) -> Optional[dict]:
    if not is_public_slug(slug):
        return None
    announcement = _live(statuses, slug, timezone.now())
    return serialize(announcement, absolute_url, with_page_body=True) if announcement else None


# ---------------------------------------------------------------- rendering and caching

def render(payload) -> RenderedResponse:
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return RenderedResponse(body=body, etag=f'"{hashlib.sha256(body).hexdigest()[:32]}"')


def _generation() -> str:
    return cache.get_or_set(GENERATION_KEY, lambda: secrets.token_hex(8), None)


def invalidate_cache():
    """Every cached body is keyed by the generation, so a new one drops them all at once."""
    cache.set(GENERATION_KEY, secrets.token_hex(8), None)


def _cached(name: str, build: Callable[[], Optional[RenderedResponse]]) -> Optional[RenderedResponse]:
    key = f'announcements:{_generation()}:{name}'
    entry = cache.get(key)
    if entry is None:
        rendered = build()
        entry = {'body': rendered.body, 'etag': rendered.etag} if rendered else {'missing': True}
        cache.set(key, entry, CACHE_SECONDS)
    return None if entry.get('missing') else RenderedResponse(entry['body'], entry['etag'])


def public_list(absolute_url: AbsoluteUrl) -> RenderedResponse:
    return _cached('list', lambda: render(list_payload(absolute_url)))


def public_detail(slug: str, absolute_url: AbsoluteUrl) -> Optional[RenderedResponse]:
    def build():
        payload = detail_payload(slug, absolute_url)
        return render(payload) if payload else None
    return _cached(f'item:{slug}', build)


def is_preview_token(token: str) -> bool:
    expected = AnnouncementSettings.load().preview_token
    return bool(token) and bool(expected) and secrets.compare_digest(token, expected)
