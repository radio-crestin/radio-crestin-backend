import json
import secrets

from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import PlaylistItemType, StationKind, StationPlaylistItems, Stations

MAX_ITEMS = 500
MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 500
MAX_THUMBNAIL_URL_LENGTH = 200  # matches URLField max_length on the model


@method_decorator(csrf_exempt, name='dispatch')
class StationPlaylistUpdateView(View):
    """Full-replace a playlist station's items, authorized by its API key.

    POST /api/v1/station-playlist/update
    Headers: ``X-Api-Key: <station playlist_api_key>``
             (``Authorization: Bearer <key>`` also accepted)
    Body (JSON): {
        "station_slug": "<slug>",
        "items": [
            {"type": "audio" | "video" | "youtube" | "youtube_playlist",
             "url": "...",                      # required, non-empty
             "title": "...",                    # optional, default ""
             "thumbnail_url": null,             # optional
             "duration_seconds": null,          # optional, non-negative int
             "enabled": true},                  # optional, default true
            ...                                 # max 500 items
        ]
    }

    The items array is authoritative: the station's existing playlist items
    are deleted and replaced in one atomic transaction, ordered by array
    position (playlist_item_order = 1..n).

    Response 200 mirrors the GET /api/v1/station-playlist station object
    (a single ``station`` instead of the ``stations`` array; enabled items
    only, in client playback order):
        {"data": {"station": {"id", "slug", "station_type", "playlist_items":
            [{"id", "order", "type", "url", "title", "thumbnail_url",
              "duration_seconds"}, ...]}}}

    Apps pick the change up within ~5-10 seconds: the GET endpoint's URLs
    rotate on a 5-second timestamp window, so no cache purge is needed.

    Auth failures (missing/wrong key, unknown slug, non-playlist station)
    all return the same 401 to avoid leaking which stations exist.
    """

    def post(self, request):
        try:
            data = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return self._error(400, 'Invalid JSON body.')
        if not isinstance(data, dict):
            return self._error(400, 'Expected a JSON object.')

        provided_key = self._extract_api_key(request)
        station_slug = str(data.get('station_slug') or '').strip()

        # One shared 401 for unknown slug / non-playlist station / bad key,
        # so callers can't probe which stations exist.
        station = Stations.objects.filter(
            slug=station_slug, station_type=StationKind.PLAYLIST,
        ).first() if station_slug else None
        expected_key = station.playlist_api_key if station else ''
        if not provided_key or not expected_key or not secrets.compare_digest(
            provided_key.encode('utf-8'), expected_key.encode('utf-8'),
        ):
            return self._error(401, 'Invalid API key or station.')

        items, validation_error = self._validate_items(data.get('items'))
        if validation_error:
            return self._error(400, validation_error)

        with transaction.atomic():
            station.playlist_items.all().delete()
            # bulk_create skips model save(), so mirror its float->int
            # rounding by writing both order fields explicitly.
            StationPlaylistItems.objects.bulk_create([
                StationPlaylistItems(
                    station=station,
                    type=item['type'],
                    url=item['url'],
                    title=item['title'],
                    thumbnail_url=item['thumbnail_url'],
                    duration_seconds=item['duration_seconds'],
                    order=index,
                    playlist_item_order=index,
                    enabled=item['enabled'],
                )
                for index, item in enumerate(items, start=1)
            ])

        fresh_items = station.playlist_items.filter(
            enabled=True,
        ).order_by('playlist_item_order', 'id')
        response = JsonResponse({'data': {'station': {
            'id': station.id,
            'slug': station.slug,
            'station_type': station.station_type,
            'playlist_items': [
                {
                    'id': item.id,
                    'order': item.order,
                    'type': item.type,
                    'url': item.url,
                    'title': item.title,
                    'thumbnail_url': item.thumbnail_url,
                    'duration_seconds': item.duration_seconds,
                }
                for item in fresh_items
            ],
        }}})
        return self._add_headers(response)

    @staticmethod
    def _extract_api_key(request) -> str:
        """API key from X-Api-Key, or Authorization: Bearer as a fallback."""
        key = (request.headers.get('X-Api-Key') or '').strip()
        if key:
            return key
        authorization = (request.headers.get('Authorization') or '').strip()
        if authorization.lower().startswith('bearer '):
            return authorization[len('bearer '):].strip()
        return ''

    @staticmethod
    def _validate_items(raw):
        """Validate the items payload. Returns (items, None) or (None, error)."""
        if not isinstance(raw, list):
            return None, 'items must be a JSON array.'
        if len(raw) > MAX_ITEMS:
            return None, f'Too many items (max {MAX_ITEMS}).'

        valid_types = set(PlaylistItemType.values)
        items = []
        for index, entry in enumerate(raw):
            label = f'items[{index}]'
            if not isinstance(entry, dict):
                return None, f'{label} must be a JSON object.'

            item_type = entry.get('type')
            if item_type not in valid_types:
                return None, (
                    f"{label}.type must be one of: "
                    f"{', '.join(sorted(valid_types))}."
                )

            url = str(entry.get('url') or '').strip()
            if not url:
                return None, f'{label}.url is required and must be non-empty.'
            if len(url) > MAX_URL_LENGTH:
                return None, f'{label}.url is too long (max {MAX_URL_LENGTH} characters).'

            title = str(entry.get('title') or '').strip()[:MAX_TITLE_LENGTH]

            thumbnail_url = entry.get('thumbnail_url')
            if thumbnail_url is not None:
                thumbnail_url = str(thumbnail_url).strip() or None
            if thumbnail_url and len(thumbnail_url) > MAX_THUMBNAIL_URL_LENGTH:
                return None, (
                    f'{label}.thumbnail_url is too long '
                    f'(max {MAX_THUMBNAIL_URL_LENGTH} characters).'
                )

            duration_seconds = entry.get('duration_seconds')
            if duration_seconds is not None and (
                isinstance(duration_seconds, bool)
                or not isinstance(duration_seconds, int)
                or duration_seconds < 0
            ):
                return None, f'{label}.duration_seconds must be a non-negative integer or null.'

            enabled = entry.get('enabled', True)
            if not isinstance(enabled, bool):
                return None, f'{label}.enabled must be a boolean.'

            items.append({
                'type': item_type,
                'url': url,
                'title': title,
                'thumbnail_url': thumbnail_url,
                'duration_seconds': duration_seconds,
                'enabled': enabled,
            })

        return items, None

    @classmethod
    def _error(cls, status, message):
        return cls._add_headers(JsonResponse({'error': message}, status=status))

    @staticmethod
    def _add_headers(response):
        response['Cache-Control'] = 'no-store'
        response['Access-Control-Allow-Origin'] = '*'
        return response
