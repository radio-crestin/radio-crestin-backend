import json
import re
from typing import Any, Dict, Optional

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter


class IcecastScraper(BaseScraper):
    """Scraper for Icecast stats JSON API"""

    def get_scraper_type(self) -> str:
        return "icecast"

    def extract_data(self, response_data: Any, config=None) -> StationNowPlayingData:
        """Extract data from Icecast JSON response"""

        # Convert JSON string to dict if needed
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except (json.JSONDecodeError, ValueError):
                return StationNowPlayingData(current_song=None, listeners=None)

        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)

        # Extract listen_url and server_url from the original URL if available
        # This would need to be passed in via kwargs in practice
        source = self._find_source(response_data)

        if not source:
            return StationNowPlayingData(current_song=None, listeners=None)

        raw_title = source.get("title", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title, config)

        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )

        listeners = source.get("listeners")
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

    def _find_source(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the appropriate source from Icecast response"""
        icestats = data.get("icestats", {})
        source = icestats.get("source")

        if not source:
            return None

        # If source is a list, return the first one for now
        # In practice, you'd want to match by listen_url/server_url
        if isinstance(source, list):
            return source[0] if source else None

        return source

    async def _make_request(self, client, url: str, **kwargs):
        """Override to set appropriate headers for Icecast"""
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
        }
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        return await super()._make_request(client, url, **kwargs)
