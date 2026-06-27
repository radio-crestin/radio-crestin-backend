import ipaddress
import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import AppUsers


@method_decorator(csrf_exempt, name='dispatch')
class DeviceRegistrationView(View):
    """Upserts the calling device's details into AppUsers.

    POST /api/v1/devices/register/
    Body (JSON): {
        "device_id": "<persistent device id>",   # required; stored as anonymous_id
        "platform": "android" | "ios",
        "os_version": "16", "device_model": "Pixel 8",
        "manufacturer": "Google", "app_version": "1.3.2",
        "build_number": "56", "locale": "ro_RO", "timezone": "EEST",
        "is_physical_device": true, "fcm_token": "...",
        ... any extra fields (brand, screen size, ABIs, ...) ...
    }
    Response: { "status": "ok", "created": bool }

    The mobile app calls this on every launch, so it's an idempotent
    ``update_or_create`` keyed by ``anonymous_id``. The public IP is taken from
    the request headers (server-side) and never trusted from the body. The full
    payload is stored verbatim in ``device_info``; the mapped keys also populate
    dedicated columns for easy filtering in the admin.
    """

    # src key in the JSON body -> (AppUsers column, max length)
    _COLUMN_KEYS = {
        'platform': ('device_platform', 64),
        'device_model': ('device_model', 255),
        'manufacturer': ('device_manufacturer', 255),
        'os_version': ('device_os_version', 64),
        'app_version': ('device_app_version', 64),
        'build_number': ('device_build_number', 64),
        'locale': ('device_locale', 64),
        'timezone': ('device_timezone', 64),
    }

    def post(self, request):
        try:
            data = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest('invalid json')

        if not isinstance(data, dict):
            return HttpResponseBadRequest('expected a json object')

        device_id = str(data.get('device_id') or '').strip()
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)

        now = timezone.now()
        defaults = {
            'device_last_ip': self._safe_ip(self._get_client_ip(request)),
            'device_last_seen_at': now,
            'device_info': data,
        }

        for src, (col, maxlen) in self._COLUMN_KEYS.items():
            value = data.get(src)
            if value is not None and value != '':
                defaults[col] = str(value)[:maxlen]

        is_physical = data.get('is_physical_device')
        if isinstance(is_physical, bool):
            defaults['device_is_physical'] = is_physical

        fcm_token = data.get('fcm_token')
        if fcm_token:
            defaults['device_fcm_token'] = str(fcm_token)

        user, created = AppUsers.objects.update_or_create(
            anonymous_id=device_id,
            defaults=defaults,
        )

        # Stamp first-seen exactly once.
        if user.device_first_seen_at is None:
            user.device_first_seen_at = now
            user.save(update_fields=['device_first_seen_at'])

        response = JsonResponse({'status': 'ok', 'created': created})
        response['Cache-Control'] = 'no-store'
        response['Access-Control-Allow-Origin'] = '*'
        return response

    @staticmethod
    def _safe_ip(value):
        """Return a normalized IP string, or None if it isn't a valid IP."""
        try:
            return str(ipaddress.ip_address(value)) if value else None
        except ValueError:
            return None

    @staticmethod
    def _get_client_ip(request) -> str:
        """Client IP from proxy headers, mirroring the GraphQL mutation helper.

        Priority: CF-Connecting-IP (Cloudflare) -> X-Real-IP (Nginx) ->
        X-Forwarded-For (first hop) -> REMOTE_ADDR.
        """
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip:
            return cf_connecting_ip.strip()
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip.strip()
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
