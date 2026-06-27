import hashlib

from django.http import JsonResponse
from django.views import View

from ..models import SessionRecordingConfig, SessionRecordingOverride


class SessionRecordingView(View):
    """Tells the app whether a given device should record its screen.

    GET /api/v1/session-recording/<device_id>/
    Response: { "should_record": bool, "sample_rate": float }

    Decision order:
      1. A manual override for this device id wins (force on/off).
      2. Else, if the master switch is on, the device records when it falls
         inside the rollout percentage (deterministic by device id).
      3. Else, no recording.
    """

    @staticmethod
    def _bucket(device_id: str) -> int:
        """Stable 0-99 bucket for a device id (consistent across processes)."""
        digest = hashlib.sha256(device_id.encode('utf-8')).hexdigest()
        return int(digest, 16) % 100

    def get(self, request, device_id: str):
        device_id = (device_id or '').strip()
        config = SessionRecordingConfig.objects.first()
        sample_rate = config.sample_rate if config else 1.0

        # 1. Manual per-device override wins.
        if device_id:
            override = (
                SessionRecordingOverride.objects
                .filter(device_id=device_id)
                .first()
            )
            if override is not None:
                return self._response(override.enabled, sample_rate)

        # 2. Percentage rollout — only when the master switch is on.
        if config and config.enabled and device_id:
            should_record = self._bucket(device_id) < config.rollout_percentage
            return self._response(should_record, sample_rate)

        # 3. Default: do not record.
        return self._response(False, sample_rate)

    @staticmethod
    def _response(should_record: bool, sample_rate: float) -> JsonResponse:
        response = JsonResponse({
            'should_record': should_record,
            'sample_rate': sample_rate,
        })
        # Decision is per device — never cache it at the CDN.
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        return response
