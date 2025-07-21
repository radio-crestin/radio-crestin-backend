import json
from typing import Any, Dict

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter


class ShoutcastScraper(BaseScraper):
    """Scraper for Shoutcast stats JSON API"""

    def get_scraper_type(self) -> str:
        return "shoutcast"

    def extract_data(self, response_data: Any, config=None) -> StationNowPlayingData:
        """Extract data from Shoutcast JSON response"""
        # Convert JSON string to dict if needed
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except (json.JSONDecodeError, ValueError):
                return StationNowPlayingData(current_song=None, listeners=None)
        
        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)

        raw_title = response_data.get("songtitle", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title, config)

        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )

        listeners = response_data.get("currentlisteners")
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

    async def _make_request(self, client, url: str, **kwargs):
        """Override to set appropriate headers for Shoutcast"""
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
        }
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        return await super()._make_request(client, url, **kwargs)
