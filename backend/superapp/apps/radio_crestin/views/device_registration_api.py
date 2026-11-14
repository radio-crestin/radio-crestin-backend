import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import AppUsers
from ..utils.client_request import client_country, client_ip, safe_ip
from ..utils.rate_limits import over_limit

# The app's payload is ~1 KB; device_info stores it verbatim.
MAX_BODY_BYTES = 16 * 1024
MAX_DEVICE_ID_LENGTH = 512  # AppUsers.anonymous_id
MAX_FCM_TOKEN_LENGTH = 4096
# The app registers on every launch: generous per IP (carrier NAT), tight per device.
RATE_PER_IP = '600/h'
RATE_PER_DEVICE = '30/h'


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
    Response: { "status": "ok", "created": bool, "country": "RO" | null }

    The mobile app calls this on every launch, so it's an idempotent
    ``update_or_create`` keyed by ``anonymous_id``. The public IP is taken from
    the request headers (server-side) and never trusted from the body, and so is
    the country (Cloudflare's CF-IPCountry; kept unchanged when unknown). The full
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
        ip = safe_ip(client_ip(request))
        if over_limit(request, 'device-register-ip', ip, RATE_PER_IP):
            return JsonResponse({'error': 'rate limited'}, status=429)
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY_BYTES or len(request.body) > MAX_BODY_BYTES:
            return JsonResponse({'error': 'payload too large'}, status=413)
        try:
            data = json.loads((request.body or b'{}').decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return HttpResponseBadRequest('invalid json')

        if not isinstance(data, dict):
            return HttpResponseBadRequest('expected a json object')

        device_id = str(data.get('device_id') or '').strip()
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        if len(device_id) > MAX_DEVICE_ID_LENGTH:
            return JsonResponse({'error': 'device_id is too long'}, status=400)
        if over_limit(request, 'device-register-device', device_id, RATE_PER_DEVICE):
            return JsonResponse({'error': 'rate limited'}, status=429)

        now = timezone.now()
        defaults = {
            'device_last_ip': ip,
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

        country = client_country(request)
        if country:
            defaults['device_country'] = country

        fcm_token = str(data.get('fcm_token') or '')
        if len(fcm_token) > MAX_FCM_TOKEN_LENGTH:
            return JsonResponse({'error': 'fcm_token is too long'}, status=400)
        if fcm_token:
            defaults['device_fcm_token'] = fcm_token
            if fcm_token != self._stored_push_token(device_id):
                defaults['device_push_token_updated_at'] = now

        user, created = AppUsers.objects.update_or_create(
            anonymous_id=device_id,
            defaults=defaults,
        )

        # Stamp first-seen exactly once.
        if user.device_first_seen_at is None:
            user.device_first_seen_at = now
            user.save(update_fields=['device_first_seen_at'])

        # The country lets the app evaluate the announcements' country filters.
        response = JsonResponse({'status': 'ok', 'created': created, 'country': country})
        response['Cache-Control'] = 'no-store'
        response['Access-Control-Allow-Origin'] = '*'
        return response

    @staticmethod
    def _stored_push_token(device_id):
        return AppUsers.objects.filter(anonymous_id=device_id).values_list('device_fcm_token', flat=True).first()
