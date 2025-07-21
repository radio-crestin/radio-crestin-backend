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
            # Use ffmpeg.probe to get metadata with modern parameters
            probe_data = ffmpeg.probe(
                url,
                v='quiet',  # Reduce verbose output
                print_format='json',  # Ensure JSON output
                show_format=None,
                show_streams=None,
                timeout=5.0,
                analyzeduration=1000000,  # 1 second in microseconds
                probesize=32768  # 32KB
            )
            
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
            
            if metadata:
                logger.info(f"Extracted metadata using ffmpeg: {list(metadata.keys())}")
            else:
                logger.warning(f"No metadata found in stream: {url}")
                
            return metadata
            
        except ffmpeg.Error as e:
            # ffmpeg errors contain stderr output with details
            stderr_output = ""
            if hasattr(e, 'stderr') and e.stderr:
                stderr_output = e.stderr.decode('utf-8') if isinstance(e.stderr, bytes) else str(e.stderr)
            
            logger.error(f"FFmpeg error probing stream {url}: {stderr_output or str(e)}")
            
            if settings.DEBUG:
                logger.debug(f"FFmpeg command that failed: {getattr(e, 'cmd', 'unknown')}")
                
            return {}
        except TimeoutError as e:
            logger.warning(f"Timeout probing stream {url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error probing stream {url}: {e}")
            if settings.DEBUG:
                logger.exception(f"Full exception for stream {url}")
            return {}

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
