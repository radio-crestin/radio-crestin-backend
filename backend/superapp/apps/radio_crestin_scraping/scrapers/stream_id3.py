import json
from typing import Any, Dict, Optional
import logging
import asyncio

import ffmpeg
from django.conf import settings

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter

logger = logging.getLogger(__name__)


class StreamId3Scraper(BaseScraper):
    """Scraper for stream ID3 metadata using ffmpeg-python"""

    def get_scraper_type(self) -> str:
        return "stream_id3"

    async def scrape(self, url: str, config=None, **kwargs) -> StationNowPlayingData:
        """Override scrape method to use ffmpeg-python"""
        logger.info(f"Scraping ID3 from stream: {url}")

        try:
            data = await self._probe_stream_async(url)
            result = self.extract_data(data, config)
            return DataFormatter.format_station_data(result)

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error scraping ID3 from {url}: {error}")
            return StationNowPlayingData(
                current_song=None,
                listeners=None,
                error=[self._serialize_error(error)]
            )

    async def _probe_stream_async(self, url: str) -> Dict[str, Any]:
        """Probe stream metadata asynchronously using ffmpeg"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._probe_stream, url)

    def _probe_stream(self, url: str) -> Dict[str, Any]:
        """Probe stream metadata using ffmpeg-python"""
        try:
            # Use ffmpeg.probe to get metadata with improved connection handling
            probe_data = ffmpeg.probe(
                url,
                v='quiet',  # Reduce verbose output
                print_format='json',  # Ensure JSON output
                show_format=None,
                show_streams=None,
                timeout=15,  # Increased timeout to 15 seconds
                analyzeduration=2000000,  # 2 seconds in microseconds
                probesize=65536,  # 64KB
                **{
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'rw_timeout': '15000000',  # 15 second read/write timeout in microseconds
                    'reconnect': '1',  # Enable reconnection
                    'reconnect_streamed': '1',  # Reconnect on streamed content
                    'reconnect_delay_max': '4',  # Max delay between reconnection attempts
                    'multiple_requests': '1',  # Allow multiple HTTP requests
                    'seekable': '0',  # Don't try to seek (for live streams)
                    'http_persistent': '0',  # Don't use persistent connections for streams
                }
            )
            
            metadata = self._extract_metadata_from_probe(probe_data)
            
            if metadata:
                logger.info(f"Extracted metadata using ffmpeg: {list(metadata.keys())}")
            else:
                logger.warning(f"No metadata found in stream: {url}")
                
            return metadata
            
        except ffmpeg.Error as e:
            # Extract all available error information
            stderr_output = 'No stderr output'
            stdout_output = 'No stdout output'
            
            # Try to extract stderr from args if available
            if hasattr(e, 'stderr') and e.stderr:
                if isinstance(e.stderr, bytes):
                    stderr_output = e.stderr.decode('utf-8', errors='replace')
                else:
                    stderr_output = str(e.stderr)
            elif len(e.args) >= 2 and e.args[1]:
                # Sometimes stderr is in args[1]
                if isinstance(e.args[1], bytes):
                    stderr_output = e.args[1].decode('utf-8', errors='replace')
                else:
                    stderr_output = str(e.args[1])
                    
            # Try to extract stdout
            if hasattr(e, 'stdout') and e.stdout:
                if isinstance(e.stdout, bytes):
                    stdout_output = e.stdout.decode('utf-8', errors='replace')
                else:
                    stdout_output = str(e.stdout)
            elif len(e.args) >= 3 and e.args[2]:
                # Sometimes stdout is in args[2]
                if isinstance(e.args[2], bytes):
                    stdout_output = e.args[2].decode('utf-8', errors='replace')
                else:
                    stdout_output = str(e.args[2])
            
            # Try to extract command and return code
            cmd_info = 'unknown command'
            returncode = 'unknown'
            
            if len(e.args) >= 1:
                cmd_info = str(e.args[0]) if e.args[0] else 'unknown command'
            
            if hasattr(e, 'returncode'):
                returncode = e.returncode
            elif hasattr(e, 'code'):
                returncode = e.code
            
            error_msg = f"FFmpeg error probing stream {url}: {str(e)}"
            if stderr_output != 'No stderr output':
                error_msg += f"\nStderr: {stderr_output}"
            if stdout_output != 'No stdout output':
                error_msg += f"\nStdout: {stdout_output}"
            
            logger.error(error_msg)
            
            if settings.DEBUG:
                # In debug mode, log more details but don't re-raise to avoid breaking the scraping
                logger.error(f"Full ffmpeg error details - Command: {cmd_info}, Return code: {returncode}")
                
            return {}
        except TimeoutError as e:
            logger.warning(f"Timeout probing stream {url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error probing stream {url}: {e}")
            if settings.DEBUG:
                logger.exception(f"Full exception for stream {url}")
                
            # Try a simpler ffmpeg approach as fallback
            try:
                logger.info(f"Attempting fallback simple probe for {url}")
                simple_probe_data = ffmpeg.probe(url, timeout=10)
                if simple_probe_data:
                    logger.info(f"Fallback probe succeeded for {url}")
                    return self._extract_metadata_from_probe(simple_probe_data)
            except Exception as fallback_error:
                logger.warning(f"Fallback probe also failed for {url}: {fallback_error}")
                
            return {}

    def _extract_metadata_from_probe(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from probe data"""
        metadata = {}
        
        # Extract format-level metadata (includes ICY metadata for streams)
        if 'format' in probe_data and 'tags' in probe_data['format']:
            format_tags = probe_data['format']['tags']
            
            # Common ICY/streaming metadata fields
            for key, value in format_tags.items():
                key_lower = key.lower()
                if key_lower in ['title', 'icy-name', 'streamtitle']:
                    metadata['title'] = value
                elif key_lower in ['artist', 'icy-artist']:
                    metadata['artist'] = value
                elif key_lower in ['album', 'icy-album']:
                    metadata['album'] = value
                elif key_lower in ['genre', 'icy-genre']:
                    metadata['genre'] = value
                elif key_lower in ['icy-url']:
                    metadata['url'] = value
                else:
                    # Store all other metadata as-is
                    metadata[key] = value
        
        # Extract stream-level metadata
        if 'streams' in probe_data:
            for stream in probe_data['streams']:
                if stream.get('codec_type') == 'audio' and 'tags' in stream:
                    stream_tags = stream['tags']
                    
                    # ID3 tags from audio stream
                    for key, value in stream_tags.items():
                        key_lower = key.lower()
                        if key_lower == 'title' and not metadata.get('title'):
                            metadata['title'] = value
                        elif key_lower == 'artist' and not metadata.get('artist'):
                            metadata['artist'] = value
                        elif key_lower == 'album' and not metadata.get('album'):
                            metadata['album'] = value
                        elif key_lower == 'genre' and not metadata.get('genre'):
                            metadata['genre'] = value
                        elif key not in metadata:
                            metadata[key] = value
        
        return metadata

    def extract_data(self, response_data: Any, config=None) -> StationNowPlayingData:
        """Extract data from mutagen response"""

        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)

        # Get title from common fields, prioritizing the 'title' key from our extraction
        raw_title = response_data.get("title", "")

        # If no title found, try other sources
        if not raw_title:
            raw_title = response_data.get("TIT2", "")

        # Parse artist and song name
        song_name, artist = DataFormatter.parse_title_artist(raw_title, config)

        # Also try to get artist directly from ID3 tags
        if not artist:
            artist = response_data.get("artist", "") or response_data.get("TPE1", "")

        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )

        # Listeners info is typically not available in ID3 tags of streams
        listeners = response_data.get("listeners")
        if listeners is not None:
            try:
                listeners = int(listeners)
            except (ValueError, TypeError):
                listeners = None

        return StationNowPlayingData(
            current_song=song_data,
            listeners=listeners,
            raw_data=[response_data]
        )
