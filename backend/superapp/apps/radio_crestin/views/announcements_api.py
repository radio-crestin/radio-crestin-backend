import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..services import announcement_events, announcement_feed
from ..services.announcement_targeting import Audience
from ..utils.client_request import client_country, client_ip, safe_ip


def _json(data, status=200) -> JsonResponse:
    response = JsonResponse(data, status=status)
    # Targeting is per device: never cache at the CDN.
    response['Cache-Control'] = 'private, no-store'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def _absolute(request, url):
    return request.build_absolute_uri(url) if url and url.startswith('/') else url


def _with_absolute_urls(request, payload: dict) -> dict:
    """Local file storage gives relative URLs; clients need absolute ones."""
    payload = {**payload, 'icon': {**payload['icon'], 'url': _absolute(request, payload['icon']['url'])}}
    if payload['page']:
        page = payload['page']
        payload['page'] = {**page, 'cover_image_url': _absolute(request, page['cover_image_url'])}
    return payload


class AnnouncementListView(View):
    """GET /api/v1/announcements/?device_id=&platform=web|android|ios&app_version=&locale=&viewport=mobile|desktop"""

    def get(self, request):
        params = request.GET
        audience = Audience(
            platform=params.get('platform', ''),
            viewport=params.get('viewport', ''),
            country=client_country(request) or '',
            locale=params.get('locale', ''),
            device_id=params.get('device_id', ''),
            ip=safe_ip(client_ip(request)) or '',
            app_version=params.get('app_version', ''),
        )
        feed = announcement_feed.announcements_for(audience)
        feed['announcements'] = [_with_absolute_urls(request, item) for item in feed['announcements']]
        return _json(feed)


class AnnouncementDetailView(View):
    """GET /api/v1/announcements/<slug>/ — active and in its time window, no targeting."""

    def get(self, request, slug: str):
        payload = announcement_feed.live_announcement(slug)
        if payload is None:
            return _json({'error': 'not found'}, status=404)
        return _json(_with_absolute_urls(request, payload))


@method_decorator(csrf_exempt, name='dispatch')
class AnnouncementEventsView(View):
    """POST /api/v1/announcements/events/

    The body is JSON whatever the Content-Type: the website sends text/plain
    through navigator.sendBeacon to avoid a CORS preflight.
    """

    def post(self, request):
        try:
            payload = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return _json({'error': 'invalid json'}, status=400)
        if not isinstance(payload, dict):
            return _json({'error': 'expected a json object'}, status=400)

        accepted = announcement_events.ingest(
            payload, country=client_country(request) or '', ip=safe_ip(client_ip(request)),
        )
        return _json({'status': 'ok', 'accepted': accepted})

    def options(self, request, *args, **kwargs):
        response = _json({})
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Access-Control-Max-Age'] = '86400'
        return response
