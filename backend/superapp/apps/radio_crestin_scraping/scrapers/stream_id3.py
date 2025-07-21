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
            # Fetch stream data with httpx
            with httpx.stream('GET', url, timeout=30.0) as response:
                response.raise_for_status()
                
                # Read enough data to get ID3 tags (typically first few KB)
                stream_data = b""
                for chunk in response.iter_bytes(chunk_size=8192):
                    stream_data += chunk
                    # Read up to 64KB to ensure we get ID3 tags
                    if len(stream_data) >= 65536:
                        break
                
                # Create a file-like object from the stream data
                stream_file = io.BytesIO(stream_data)
                
                # Try to parse ID3 tags using mutagen
                try:
                    audio_file = self.MutagenFile(stream_file)
                    if audio_file is None:
                        # Try direct ID3 parsing
                        stream_file.seek(0)
                        audio_file = self.ID3(stream_file)
                except (self.ID3NoHeaderError, Exception):
                    # If no ID3 header found, try just ID3 parsing
                    try:
                        stream_file.seek(0)
                        audio_file = self.ID3(stream_file)
                    except Exception:
                        logger.warning(f"No ID3 tags found in stream: {url}")
                        return {}
                
                # Extract metadata
                metadata = {}
                if audio_file:
                    # Convert mutagen tags to dict format
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
                    
                    # Extract common fields
                    if 'TIT2' in metadata:
                        metadata['title'] = metadata['TIT2']
                    if 'TPE1' in metadata:
                        metadata['artist'] = metadata['TPE1']
                    if 'TALB' in metadata:
                        metadata['album'] = metadata['TALB']
                
                return metadata
                
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
