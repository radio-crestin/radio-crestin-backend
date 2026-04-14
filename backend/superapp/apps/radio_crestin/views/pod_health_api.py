import json
import os

from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from ..models import Stations


def _check_api_key(request) -> bool:
    """Validate the streaming pod API key."""
    key = request.headers.get('X-Streaming-Api-Key', '')
    expected = os.getenv('STREAMING_POD_API_KEY', 'dev-streaming-key')
    return key == expected


@method_decorator(csrf_exempt, name='dispatch')
class PodHealthReportView(View):
    """
    Streaming pod reports its FFmpeg health status.

    POST /api/v1/pod-health/
    Body: {station_slug, is_up, latency_ms?, reason?}

    Updates the station's uptime record using the same UptimeService
    that the external uptime checker uses.
    """

    def post(self, request):
        if not _check_api_key(request):
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        station_slug = body.get('station_slug')
        if not station_slug:
            return JsonResponse({'error': 'station_slug required'}, status=400)

        try:
            station = Stations.objects.only('id', 'check_uptime').get(slug=station_slug)
        except Stations.DoesNotExist:
            return JsonResponse({'error': f'Station {station_slug} not found'}, status=404)

        from superapp.apps.radio_crestin_scraping.services.uptime_service import UptimeService
        from superapp.apps.radio_crestin_scraping.utils.data_types import StationUptimeData

        is_up = body.get('is_up', True)
        latency_ms = body.get('latency_ms', 0)
        reason = body.get('reason', '')

        data = StationUptimeData(
            timestamp=timezone.now(),
            is_up=is_up,
            latency_ms=latency_ms,
            raw_data={
                'source': 'ffmpeg_pod',
                'reason': reason,
                'station_slug': station_slug,
            },
        )

        success = UptimeService.upsert_station_uptime(station.id, data)
        return JsonResponse({'success': success})
