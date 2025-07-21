import json
from typing import Any, Dict, Optional
import logging
import io
import httpx

from django.conf import settings

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter

logger = logging.getLogger(__name__)


class StreamId3Scraper(BaseScraper):
    """Scraper for stream ID3 metadata"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import mutagen library
        from mutagen import File as MutagenFile
        from mutagen.id3 import ID3, ID3NoHeaderError
        self.MutagenFile = MutagenFile
        self.ID3 = ID3
        self.ID3NoHeaderError = ID3NoHeaderError

    def get_scraper_type(self) -> str:
        return "stream_id3"

    async def scrape(self, url: str, **kwargs) -> StationNowPlayingData:
        """Override scrape method to use mutagen library"""
        logger.info(f"Scraping ID3 from stream: {url}")

        try:
            # Use mutagen library to parse stream
            data = await self._parse_stream_async(url)
            result = self.extract_data(data)
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

    async def _parse_stream_async(self, url: str) -> Dict[str, Any]:
        """Parse stream ID3 data asynchronously"""
        import asyncio

        # Run the blocking mutagen call in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_id3_stream, url)

    def _parse_id3_stream(self, url: str) -> Dict[str, Any]:
        """Parse stream ID3 data using mutagen"""
        try:
            # Use shorter timeout for stream connections
            timeout = httpx.Timeout(connect=10.0, read=10.0, write=10.0, pool=10.0)
            
            # Fetch stream data with httpx
            with httpx.stream('GET', url, timeout=timeout, follow_redirects=True) as response:
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                logger.info(f"Stream content type: {content_type}")
                
                # Read limited amount of data to get ID3 tags
                stream_data = b""
                max_bytes = 65536  # 64KB max
                bytes_read = 0
                
                try:
                    for chunk in response.iter_bytes(chunk_size=4096):
                        stream_data += chunk
                        bytes_read += len(chunk)
                        
                        # Stop if we've read enough data
                        if bytes_read >= max_bytes:
                            break
                        
                        # For streams, ID3 tags are usually at the beginning
                        # If we have some data, try to find ID3 header
                        if len(stream_data) >= 10:  # ID3 header is 10 bytes
                            # Check for ID3v2 header (starts with "ID3")
                            if stream_data[:3] == b'ID3':
                                # ID3v2 header found, read the size
                                # Bytes 6-9 contain the tag size (synchsafe integer)
                                if len(stream_data) >= 10:
                                    tag_size = (
                                        (stream_data[6] & 0x7F) << 21 |
                                        (stream_data[7] & 0x7F) << 14 |
                                        (stream_data[8] & 0x7F) << 7 |
                                        (stream_data[9] & 0x7F)
                                    ) + 10  # Add header size
                                    
                                    # Read until we have the full tag
                                    if len(stream_data) >= tag_size:
                                        # We have the complete ID3 tag
                                        stream_data = stream_data[:tag_size]
                                        break
                                    elif bytes_read >= max_bytes:
                                        # We've read max bytes, use what we have
                                        break
                        
                        # Early exit for non-audio streams
                        if 'html' in content_type or 'text' in content_type:
                            logger.warning(f"Stream appears to be non-audio content: {content_type}")
                            return {}
                            
                except Exception as read_error:
                    logger.warning(f"Error reading stream data: {read_error}")
                    if not stream_data:
                        return {}
                
                if not stream_data:
                    logger.warning(f"No data received from stream: {url}")
                    return {}
                
                logger.info(f"Read {len(stream_data)} bytes from stream")
                
                # Create a file-like object from the stream data
                stream_file = io.BytesIO(stream_data)
                
                # Try to parse ID3 tags using mutagen
                metadata = {}
                try:
                    # First try with generic mutagen File detection
                    audio_file = self.MutagenFile(stream_file)
                    if audio_file and hasattr(audio_file, 'tags') and audio_file.tags:
                        # Extract metadata from tags
                        for key, value in audio_file.tags.items():
                            if hasattr(value, 'text'):
                                # Text frames
                                metadata[key] = value.text[0] if value.text else ""
                            elif hasattr(value, 'url'):
                                # URL frames  
                                metadata[key] = value.url
                            else:
                                # Other frame types
                                metadata[key] = str(value)
                except Exception as mutagen_error:
                    logger.debug(f"Mutagen File parsing failed: {mutagen_error}")
                
                # If no metadata found, try direct ID3 parsing
                if not metadata:
                    try:
                        stream_file.seek(0)
                        audio_file = self.ID3(stream_file)
                        if audio_file:
                            # Extract metadata from ID3 tags
                            for key, value in audio_file.items():
                                if hasattr(value, 'text'):
                                    # Text frames
                                    metadata[key] = value.text[0] if value.text else ""
                                elif hasattr(value, 'url'):
                                    # URL frames  
                                    metadata[key] = value.url
                                else:
                                    # Other frame types
                                    metadata[key] = str(value)
                    except (self.ID3NoHeaderError, Exception) as id3_error:
                        logger.debug(f"Direct ID3 parsing failed: {id3_error}")
                
                # Extract common fields if found
                if 'TIT2' in metadata:
                    metadata['title'] = metadata['TIT2']
                if 'TPE1' in metadata:
                    metadata['artist'] = metadata['TPE1']
                if 'TALB' in metadata:
                    metadata['album'] = metadata['TALB']
                
                # Check ICY headers for metadata (common in streaming)
                icy_name = response.headers.get('icy-name')
                icy_title = response.headers.get('icy-title') 
                if icy_name and not metadata.get('title'):
                    metadata['title'] = icy_name
                if icy_title and not metadata.get('title'):
                    metadata['title'] = icy_title
                
                if metadata:
                    logger.info(f"Extracted metadata: {list(metadata.keys())}")
                else:
                    logger.warning(f"No ID3 tags found in stream: {url}")
                
                return metadata
                
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to stream: {url}")
            return {}
        except httpx.RequestError as e:
            logger.error(f"Request error for stream {url}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing ID3 from stream {url}: {e}")
            return {}

    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from mutagen response"""

        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)

        # Get title from common fields, prioritizing the 'title' key from our extraction
        raw_title = response_data.get("title", "")
        
        # If no title found, try other sources
        if not raw_title:
            raw_title = response_data.get("TIT2", "")
        
        # Parse artist and song name
        song_name, artist = DataFormatter.parse_title_artist(raw_title)
        
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
