import json

from django.http import HttpResponse, HttpResponseNotModified, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.core import is_ratelimited

from ..services import announcement_events, announcement_feed
from ..utils.client_request import client_country, client_ip, safe_ip


# The list is the same for everyone, so Cloudflare may cache it. Never add s-maxage,
# no-cache or must-revalidate: they turn off Cloudflare's async stale-while-revalidate.
PUBLIC_CACHE_CONTROL = 'public, max-age=60, stale-while-revalidate=86400, stale-if-error=604800'
PRIVATE_CACHE_CONTROL = 'private, no-store'


def _with_cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _json(data, status=200) -> JsonResponse:
    """Per-request answers (events, preview, errors): never cached."""
    response = JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})
    response['Cache-Control'] = PRIVATE_CACHE_CONTROL
    return _with_cors(response)


def _etag_matches(request, etag: str) -> bool:
    sent = request.META.get('HTTP_IF_NONE_MATCH', '')
    return sent.strip() == '*' or any(tag.strip().removeprefix('W/') == etag for tag in sent.split(','))


def _public(request, rendered) -> HttpResponse:
    """A cached body with its ETag: 304 when the client already has it."""
    if _etag_matches(request, rendered.etag):
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(rendered.body, content_type='application/json')
    response['ETag'] = rendered.etag
    response['Cache-Control'] = PUBLIC_CACHE_CONTROL
    # The body already lives in Redis and is dropped on every admin change; the
    # URL-keyed page cache would keep serving a stale copy (and never answer 304).
    response._skip_page_cache = True
    return _with_cors(response)


def _absolute_url(request):
    """Local file storage gives relative URLs; clients need absolute ones."""
    return lambda url: request.build_absolute_uri(url) if url.startswith('/') else url


class AnnouncementListView(View):
    """GET /api/v1/announcements/ - every listed announcement with its filters, the same for everyone.

    `?preview=<token>` also returns the announcements in Preview, uncached; a wrong token gets 403.
    """

    def get(self, request):
        if 'preview' in request.GET:
            if not announcement_feed.is_preview_token(request.GET['preview']):
                return _json({'error': 'invalid preview token'}, status=403)
            return _json(announcement_feed.list_payload(
                _absolute_url(request), statuses=announcement_feed.PREVIEW_STATUSES,
            ))
        return _public(request, announcement_feed.public_list(_absolute_url(request)))


class AnnouncementDetailView(View):
    """GET /api/v1/announcements/<slug>/ - one announcement in its time window, with its page body."""

    def get(self, request, slug: str):
        if 'preview' in request.GET:
            if not announcement_feed.is_preview_token(request.GET['preview']):
                return _json({'error': 'invalid preview token'}, status=403)
            payload = announcement_feed.detail_payload(
                slug, _absolute_url(request), statuses=announcement_feed.PREVIEW_STATUSES,
            )
            return _json(payload) if payload else _json({'error': 'not found'}, status=404)

        rendered = announcement_feed.public_detail(slug, _absolute_url(request))
        if rendered is None:
            response = _json({'error': 'not found'}, status=404)
            response['Cache-Control'] = PUBLIC_CACHE_CONTROL
            response._skip_page_cache = True
            return response
        return _public(request, rendered)


# Generous per IP: many phones share one carrier (CGNAT) address.
EVENTS_RATE_PER_IP = '600/m'
EVENTS_RATE_PER_DEVICE = '30/m'


def _over_limit(request, group: str, value: str, rate: str) -> bool:
    return is_ratelimited(request, group=group, key=lambda _group, _request: value, rate=rate, increment=True)


@method_decorator(csrf_exempt, name='dispatch')
class AnnouncementEventsView(View):
    """POST /api/v1/announcements/events/

    The body is JSON whatever the Content-Type: the website sends text/plain
    through navigator.sendBeacon to avoid a CORS preflight. Requests over the
    per-IP or per-device rate get a 429 and nothing is stored.
    """

    def post(self, request):
        ip = safe_ip(client_ip(request))
        if _over_limit(request, 'announcement-events-ip', ip or '', EVENTS_RATE_PER_IP):
            return _json({'error': 'rate limited'}, status=429)
        try:
            payload = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return _json({'error': 'invalid json'}, status=400)
        if not isinstance(payload, dict):
            return _json({'error': 'expected a json object'}, status=400)

        device_id = str(payload.get('device_id') or '').strip()
        if device_id and _over_limit(request, 'announcement-events-device', device_id, EVENTS_RATE_PER_DEVICE):
            return _json({'error': 'rate limited'}, status=429)

        country = client_country(request)
        accepted = announcement_events.ingest(payload, country=country or '', ip=ip)
        # The country tells the website which country filters apply to it.
        return _json({'status': 'ok', 'accepted': accepted, 'country': country})

    def options(self, request, *args, **kwargs):
        response = _json({})
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Access-Control-Max-Age'] = '86400'
        return response
