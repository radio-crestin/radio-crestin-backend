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
    @transaction.atomic
    def upsert_station_uptime(station_id: int, data: StationUptimeData) -> bool:
        """Upsert station uptime data"""
        try:
            uptime, created = StationsUptime.objects.update_or_create(
                station_id=station_id,
                defaults={
                    'timestamp': data.timestamp,
                    'is_up': data.is_up,
                    'latency_ms': data.latency_ms,
                    'raw_data': data.raw_data,
                }
            )

            # Update station's latest_station_uptime reference
            Stations.objects.filter(id=station_id).update(
                latest_station_uptime=uptime
            )

            logger.info(f"{'Created' if created else 'Updated'} uptime for station {station_id}")
            return True

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error upserting station uptime for station {station_id}: {error}")
            return False