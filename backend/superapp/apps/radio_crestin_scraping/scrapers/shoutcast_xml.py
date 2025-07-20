import re
from typing import Any, Dict

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter


class ShoutcastXmlScraper(BaseScraper):
    """Scraper for Shoutcast XML stats"""
    
    def get_scraper_type(self) -> str:
        return "shoutcast_xml"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from Shoutcast XML response"""
        if not isinstance(response_data, str):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        # Parse XML using regex (matching the original implementation)
        parsed_data = self._parse_xml(response_data)
        
        raw_title = parsed_data.get("SONGTITLE", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title)
        
        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )
        
        listeners = parsed_data.get("CURRENTLISTENERS")
        if listeners is not None:
            try:
                listeners = int(listeners)
            except (ValueError, TypeError):
                listeners = None
        
        return StationNowPlayingData(
            current_song=song_data,
            listeners=listeners,
            raw_data=[parsed_data]
        )
    
    def _parse_xml(self, xml_content: str) -> Dict[str, str]:
        """Parse XML content using regex (matching original implementation)"""
        regex = re.compile(r'<(?P<param_data>[a-zA-Z\s]+)>(?P<value>.*?)</', re.MULTILINE)
        
        data = {}
        xml_content = xml_content.replace("SHOUTCASTSERVER", "")
        
        for match in regex.finditer(xml_content):
            param_data = match.group('param_data')
            value = match.group('value')
            if param_data:
                data[param_data] = value
        
        return data
    
    async def _make_request(self, client, url: str, **kwargs):
        """Override to set appropriate headers for Shoutcast XML"""
        headers = self._get_default_headers()
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        return await super()._make_request(client, url, **kwargs)