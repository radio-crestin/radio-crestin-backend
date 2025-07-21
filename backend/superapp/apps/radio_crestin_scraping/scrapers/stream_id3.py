import json
from typing import Any, Dict, Optional
import logging

from django.conf import settings

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter

logger = logging.getLogger(__name__)


class StreamId3Scraper(BaseScraper):
    """Scraper for stream ID3 metadata"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Import radio-id3 library (would need to be installed)
            from radio_id3 import parseRadioID3
            self.parse_radio_id3 = parseRadioID3
        except ImportError:
            logger.warning("radio-id3 library not available. Stream ID3 scraping will be disabled.")
            self.parse_radio_id3 = None

    def get_scraper_type(self) -> str:
        return "stream_id3"

    async def scrape(self, url: str, **kwargs) -> StationNowPlayingData:
        """Override scrape method to use radio-id3 library"""
        if not self.parse_radio_id3:
            logger.error("radio-id3 library not available")
            return StationNowPlayingData(
                current_song=None,
                listeners=None,
                error=[{"type": "ImportError", "message": "radio-id3 library not available"}]
            )

        logger.info(f"Scraping ID3 from stream: {url}")

        try:
            # Use radio-id3 library to parse stream
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

        # Run the blocking radio-id3 call in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.parse_radio_id3, url)

    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from radio-id3 response"""

        # Convert JSON string to dict if needed
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except (json.JSONDecodeError, ValueError):
                return StationNowPlayingData(current_song=None, listeners=None)

        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)

        raw_title = response_data.get("title", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title)

        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )

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
