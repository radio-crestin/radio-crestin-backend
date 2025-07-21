import logging
import time
import asyncio
from typing import Dict, Any, Optional

import ffmpeg
from django.conf import settings
from django.utils import timezone

from .base import BaseScraper
from ..utils.data_types import StationUptimeData
from ..services.uptime_service import UptimeService

logger = logging.getLogger(__name__)


class UptimeScraper(BaseScraper):
    """Scraper for checking station uptime using ffmpeg-python"""

    def get_scraper_type(self) -> str:
        return "uptime_ffmpeg"

    async def check_station_uptime(self, station_id: int) -> Dict[str, Any]:
        """Check uptime for a single station"""
        from superapp.apps.radio_crestin.models import Stations
        
        try:
            station = Stations.objects.get(id=station_id, disabled=False)
        except Stations.DoesNotExist:
            error_msg = f"Station {station_id} not found or disabled"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        result = await self._check_single_station_uptime(station)
        return result

    async def check_all_stations_uptime(self) -> Dict[str, Any]:
        """Check uptime for all active stations"""
        stations = UptimeService.get_all_active_stations()
        
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
        """Check uptime for a single station using ffmpeg and save the result"""
        start_time = time.time()
        is_up = False
        latency_ms = 0
        error_msg = None
        raw_data = {}

        try:
            # Use ffmpeg to probe the stream with timeout
            probe_data = await self._probe_stream_async(station.stream_url)
            
            # Calculate latency
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            if probe_data and 'streams' in probe_data:
                # Check if we have any audio streams
                audio_streams = [s for s in probe_data['streams'] if s.get('codec_type') == 'audio']
                
                if audio_streams:
                    is_up = True
                    raw_data = {
                        'method': 'ffmpeg_probe',
                        'audio_streams_found': len(audio_streams),
                        'format_info': probe_data.get('format', {}),
                        'streams_info': [
                            {
                                'codec_name': s.get('codec_name'),
                                'codec_type': s.get('codec_type'),
                                'sample_rate': s.get('sample_rate'),
                                'channels': s.get('channels'),
                                'bit_rate': s.get('bit_rate')
                            } for s in audio_streams
                        ]
                    }
                else:
                    error_msg = "No audio streams found in the URL"
                    raw_data = {
                        'method': 'ffmpeg_probe',
                        'error': error_msg,
                        'streams_found': len(probe_data.get('streams', [])),
                        'format_info': probe_data.get('format', {})
                    }
            else:
                error_msg = "Failed to probe stream - no valid data returned"
                raw_data = {
                    'method': 'ffmpeg_probe',
                    'error': error_msg,
                    'probe_result': probe_data
                }

        except ffmpeg.Error as e:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            stderr_output = ""
            if hasattr(e, 'stderr') and e.stderr:
                stderr_output = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            
            error_msg = f"FFmpeg error: {stderr_output or str(e)}"
            raw_data = {
                'method': 'ffmpeg_probe',
                'error': error_msg,
                'type': 'ffmpeg_error',
                'stderr': stderr_output
            }
            
            if settings.DEBUG:
                logger.debug(f"FFmpeg command that failed: {getattr(e, 'cmd', 'unknown')}")
                raise

        except asyncio.TimeoutError:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Probe timeout after {latency_ms}ms"
            raw_data = {
                'method': 'ffmpeg_probe',
                'error': error_msg,
                'type': 'timeout'
            }

        except Exception as e:
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            error_msg = f"Unexpected error: {str(e)}"
            raw_data = {
                'method': 'ffmpeg_probe',
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

    async def _probe_stream_async(self, url: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Probe stream using ffmpeg asynchronously with timeout"""
        loop = asyncio.get_event_loop()
        
        try:
            # Run with timeout to prevent hanging
            probe_data = await asyncio.wait_for(
                loop.run_in_executor(None, self._probe_stream, url),
                timeout=timeout
            )
            return probe_data
        except asyncio.TimeoutError:
            logger.warning(f"Timeout probing stream {url} after {timeout}s")
            raise

    def _probe_stream(self, url: str) -> Dict[str, Any]:
        """Probe stream using ffmpeg-python"""
        try:
            # Use ffmpeg.probe with conservative parameters for uptime checking
            probe_data = ffmpeg.probe(
                url,
                v='error',  # Only show errors
                print_format='json',
                show_format=None,
                show_streams=None,
                analyzeduration=500000,  # 0.5 seconds in microseconds - quick check
                probesize=16384,  # 16KB - minimal data needed
                timeout=8.0  # Conservative timeout
            )
            
            return probe_data
            
        except ffmpeg.Error as e:
            # Re-raise ffmpeg errors to be handled by the caller
            raise
        except Exception as e:
            logger.error(f"Unexpected error probing stream {url}: {e}")
            raise

    def extract_data(self, response_data: Any, config=None) -> Any:
        """Not used for uptime checking"""
        raise NotImplementedError("UptimeScraper does not implement extract_data method")