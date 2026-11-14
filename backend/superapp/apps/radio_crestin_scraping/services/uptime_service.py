import logging
from typing import Dict, Any
from django.db import transaction
from django.conf import settings
from django.utils import timezone

from superapp.apps.radio_crestin.models import Stations, StationsUptime
from ..utils.data_types import StationUptimeData

logger = logging.getLogger(__name__)


class UptimeService:
    """Service layer for station uptime operations"""

    @staticmethod
    def get_all_active_stations():
        """Get all active stations for uptime monitoring"""
        return Stations.objects.filter(disabled=False)

    @staticmethod
    def upsert_station_uptime(station_id: int, data: StationUptimeData) -> bool:
        """Upsert station uptime data.

        A station has one uptime row, which its latest_station_uptime points
        to from the moment it is created. Streaming pods report when their
        stream changes and at least every 60 s (~3,500 reports an hour), so
        the common case is one UPDATE; the row is created, and linked, only
        the first time.
        """
        fields = {
            'timestamp': data.timestamp,
            'is_up': data.is_up,
            'latency_ms': data.latency_ms,
            'raw_data': data.raw_data,
        }
        try:
            updated = StationsUptime.objects.filter(station_id=station_id).update(
                **fields, updated_at=timezone.now())
            if not updated:
                UptimeService._create_station_uptime(station_id, fields)
            logger.debug(f"{'Updated' if updated else 'Created'} uptime for station {station_id}")
            return True

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting station uptime for station {station_id}: {error}")
            return False

    @staticmethod
    @transaction.atomic
    def _create_station_uptime(station_id: int, fields: Dict[str, Any]) -> None:
        uptime, _ = StationsUptime.objects.update_or_create(station_id=station_id, defaults=fields)
        Stations.objects.filter(id=station_id).update(latest_station_uptime=uptime)
