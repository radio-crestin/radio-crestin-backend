import logging
import time
from typing import Dict, Any, Optional

import requests
from django.conf import settings
from django.utils import timezone

from .base import BaseScraper
from ..utils.data_types import StationUptimeData
from ..services.uptime_service import UptimeService

logger = logging.getLogger(__name__)


class UptimeScraper(BaseScraper):
    """Scraper for checking station uptime using lightweight HTTP requests"""

    def get_scraper_type(self) -> str:
        return "uptime_http"

    def check_station_uptime(self, station_id: int) -> Dict[str, Any]:
        """Check uptime for a single station"""
        from superapp.apps.radio_crestin.models import Stations

        try:
            station = Stations.objects.get(id=station_id)
            if station.disabled:
                logger.info(f"Station {station_id} is disabled - returning success with is_up=False")
                return {
                    "success": True,
                    "station_id": station.id,
                    "station_title": station.title,
                    "stream_url": station.stream_url,
                    "is_up": False,
                    "latency_ms": 0,
                    "error": "Station is disabled",
                    "raw_data": {"method": "disabled", "reason": "station_disabled"}
                }
        except Stations.DoesNotExist:
            error_msg = f"Station {station_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        result = self._check_single_station_uptime(station)
        return result

    def check_all_stations_uptime(self) -> Dict[str, Any]:
        """Check uptime for all active stations"""
        stations = UptimeService.get_all_active_stations()

        results = []
        total_checked = 0
        total_up = 0

        for station in stations:
            total_checked += 1
            result = self._check_single_station_uptime(station)
            results.append(result)
            if result["is_up"]:
                total_up += 1

            logger.info(f"Station {station.id} ({station.title}): UP={result['is_up']}, Latency={result['latency_ms']}ms")

        summary = {
            "success": True,
            "total_checked": total_checked,
            "total_up": total_up,
            "total_down": total_checked - total_up,
            "results": results
        }

        logger.info(f"Uptime check complete: {total_up}/{total_checked} stations up")
        return summary

    def _check_single_station_uptime(self, station) -> Dict[str, Any]:
        """Check uptime for a single station using lightweight HTTP request and save the result"""
        # If check_uptime is False, return True (station is considered up)
        if not getattr(station, 'check_uptime', True):
            return {
                "success": True,
                "station_id": station.id,
                "station_title": station.title,
                "stream_url": station.stream_url,
                "is_up": True,
                "latency_ms": 0,
                "error": None,
                "raw_data": {"method": "skipped", "reason": "check_uptime_disabled"}
            }

        start_time = time.time()
        is_up = False
        latency_ms = 0
        error_msg = None
        raw_data = {}

        try:
            # Use lightweight HTTP GET request to check if server responds
            response_data = self._check_stream_response(station.stream_url)

            # Calculate latency
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            if response_data['success']:
                is_up = True
                raw_data = {
                    'method': 'http_get',
                    'status_code': response_data.get('status_code'),
                    'content_type': response_data.get('content_type'),
                    'content_length': response_data.get('content_length'),
                    'headers': response_data.get('headers', {})
                }
            else:
                error_msg = response_data.get('error', 'Unknown error')
                raw_data = {
                    'method': 'http_get',
                    'error': error_msg,
                    'status_code': response_data.get('status_code'),
                    'type': response_data.get('error_type', 'http_error')
                }

        except requests.exceptions.Timeout:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Request timeout after {latency_ms}ms"
            raw_data = {
                'method': 'http_get',
                'error': error_msg,
                'type': 'timeout'
            }

        except Exception as e:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"
            raw_data = {
                'method': 'http_get',
                'error': error_msg,
                'type': 'unexpected_error'
            }

            logger.exception(f"Unexpected error checking station {station.id} ({station.title})")
            if settings.DEBUG:
                raise

        # Create uptime data
        uptime_data = StationUptimeData(
            timestamp=timezone.now().isoformat(),
            is_up=is_up,
            latency_ms=latency_ms,
            raw_data=[raw_data]
        )

        # Save to database
        try:
            UptimeService.upsert_station_uptime(station.id, uptime_data)
        except Exception as e:
            logger.error(f"Failed to save uptime data for station {station.id}: {e}")
            if settings.DEBUG:
                raise

        return {
            "success": True,
            "station_id": station.id,
            "station_title": station.title,
            "stream_url": station.stream_url,
            "is_up": is_up,
            "latency_ms": latency_ms,
            "error": error_msg,
            "raw_data": raw_data
        }

    def _check_stream_response(self, url: str, timeout: float = 3.0) -> Dict[str, Any]:
        """Check if stream responds using lightweight HTTP GET request"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; radio-crestin-scraper)',
                'Accept': '*/*',
                'Connection': 'close',
                'Range': 'bytes=0-1023'  # Only request first 1KB
            }
            
            # Use GET request with streaming and minimal data read
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            
            # Read minimal data and close immediately
            response.raw.read(1024)
            response.close()
            
            return {
                'success': True,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'content_length': response.headers.get('content-length', ''),
                'headers': {
                    'server': response.headers.get('server', ''),
                    'cache-control': response.headers.get('cache-control', ''),
                    'icy-name': response.headers.get('icy-name', ''),  # Radio stream info
                    'icy-genre': response.headers.get('icy-genre', ''),
                    'icy-br': response.headers.get('icy-br', ''),  # Bitrate
                }
            }
                    
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f'Request timeout after {timeout}s',
                'error_type': 'timeout'
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'http_client_error'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }

    def extract_data(self, response_data: Any, config=None) -> Any:
        """Not used for uptime checking"""
        raise NotImplementedError("UptimeScraper does not implement extract_data method")
