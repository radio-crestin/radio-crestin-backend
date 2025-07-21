import logging
import time
import asyncio
from typing import Dict, Any, Optional

import aiohttp
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from .base import BaseScraper
from ..utils.data_types import StationUptimeData
from ..services.uptime_service import UptimeService

logger = logging.getLogger(__name__)


class UptimeScraper(BaseScraper):
    """Scraper for checking station uptime using lightweight HTTP requests"""

    def get_scraper_type(self) -> str:
        return "uptime_http"

    async def check_station_uptime(self, station_id: int) -> Dict[str, Any]:
        """Check uptime for a single station"""
        from superapp.apps.radio_crestin.models import Stations

        try:
            station = await sync_to_async(Stations.objects.get)(id=station_id, disabled=False)
        except Stations.DoesNotExist:
            error_msg = f"Station {station_id} not found or disabled"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        result = await self._check_single_station_uptime(station)
        return result

    async def check_all_stations_uptime(self) -> Dict[str, Any]:
        """Check uptime for all active stations"""
        stations = await sync_to_async(UptimeService.get_all_active_stations)()

        results = []
        total_checked = 0
        total_up = 0

        for station in stations:
            total_checked += 1
            result = await self._check_single_station_uptime(station)
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

    async def _check_single_station_uptime(self, station) -> Dict[str, Any]:
        """Check uptime for a single station using lightweight HTTP request and save the result"""
        start_time = time.time()
        is_up = False
        latency_ms = 0
        error_msg = None
        raw_data = {}

        try:
            # Use lightweight HTTP HEAD request to check if server responds
            response_data = await self._check_stream_response(station.stream_url)

            # Calculate latency
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            if response_data['success']:
                is_up = True
                raw_data = {
                    'method': 'http_head',
                    'status_code': response_data.get('status_code'),
                    'content_type': response_data.get('content_type'),
                    'content_length': response_data.get('content_length'),
                    'headers': response_data.get('headers', {})
                }
            else:
                error_msg = response_data.get('error', 'Unknown error')
                raw_data = {
                    'method': 'http_head',
                    'error': error_msg,
                    'status_code': response_data.get('status_code'),
                    'type': response_data.get('error_type', 'http_error')
                }

        except asyncio.TimeoutError:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Request timeout after {latency_ms}ms"
            raw_data = {
                'method': 'http_head',
                'error': error_msg,
                'type': 'timeout'
            }

        except Exception as e:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"
            raw_data = {
                'method': 'http_head',
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
            await sync_to_async(UptimeService.upsert_station_uptime)(station.id, uptime_data)
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

    async def _check_stream_response(self, url: str, timeout: float = 3.0) -> Dict[str, Any]:
        """Check if stream responds using lightweight HTTP HEAD request"""
        try:
            timeout_config = aiohttp.ClientTimeout(total=timeout, connect=timeout/2)
            
            async with aiohttp.ClientSession(
                timeout=timeout_config,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; radio-crestin-scraper)',
                    'Accept': '*/*',
                    'Connection': 'close'  # Close connection immediately after response
                }
            ) as session:
                # Use HEAD request first (fastest)
                async with session.head(url, allow_redirects=True) as response:
                    return {
                        'success': True,
                        'status_code': response.status,
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
                    
        except aiohttp.ClientError as e:
            # Try GET request if HEAD fails (some servers don't support HEAD)
            try:
                timeout_config = aiohttp.ClientTimeout(total=timeout, connect=timeout/2)
                
                async with aiohttp.ClientSession(
                    timeout=timeout_config,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; radio-crestin-scraper)',
                        'Accept': '*/*',
                        'Connection': 'close',
                        'Range': 'bytes=0-1023'  # Only request first 1KB
                    }
                ) as session:
                    async with session.get(url, allow_redirects=True) as response:
                        # Read minimal data and close immediately
                        await response.read(1024)
                        
                        return {
                            'success': True,
                            'status_code': response.status,
                            'content_type': response.headers.get('content-type', ''),
                            'content_length': response.headers.get('content-length', ''),
                            'headers': {
                                'server': response.headers.get('server', ''),
                                'cache-control': response.headers.get('cache-control', ''),
                                'icy-name': response.headers.get('icy-name', ''),
                                'icy-genre': response.headers.get('icy-genre', ''),
                                'icy-br': response.headers.get('icy-br', ''),
                            }
                        }
                        
            except Exception as fallback_error:
                return {
                    'success': False,
                    'error': f"Both HEAD and GET requests failed. HEAD: {str(e)}, GET: {str(fallback_error)}",
                    'error_type': 'http_client_error'
                }
                
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'Request timeout after {timeout}s',
                'error_type': 'timeout'
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
