import re
from typing import Any, Dict

from .base import BaseScraper
from ..utils.data_types import StationNowPlayingData
from ..utils.formatters import DataFormatter


class OldIcecastHtmlScraper(BaseScraper):
    """Scraper for old Icecast HTML stats pages"""
    
    def get_scraper_type(self) -> str:
        return "old_icecast_html"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from Icecast HTML page"""
        if not isinstance(response_data, str):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        # Parse HTML using regex (matching the original implementation)
        parsed_data = self._parse_icecast_html(response_data)
        
        raw_title = parsed_data.get("Current Song", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title)
        
        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
        )
        
        listeners = parsed_data.get("Current Listeners")
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
    
    def _parse_icecast_html(self, html_content: str) -> Dict[str, str]:
        """Parse Icecast HTML content using regex"""
        regex = re.compile(
            r'<td>(?P<param_data>[a-zA-Z\s]+):</td>\n<td class="streamdata">(?P<value>.*)</td>',
            re.MULTILINE
        )
        
        data = {}
        for match in regex.finditer(html_content):
            param_data = match.group('param_data')
            value = match.group('value')
            if param_data:
                data[param_data] = value
        
        return data


class OldShoutcastHtmlScraper(BaseScraper):
    """Scraper for old Shoutcast HTML stats pages"""
    
    def get_scraper_type(self) -> str:
        return "old_shoutcast_html"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from Shoutcast HTML page"""
        if not isinstance(response_data, str):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        # Parse HTML using regex (matching the original implementation)
        parsed_data = self._parse_shoutcast_html(response_data)
        
        # Extract listeners from Stream Status field
        listeners_match = re.search(
            r'\((?P<listeners>[0-9]+) unique\)',
            parsed_data.get("Stream Status", "")
        )
        
        listeners = None
        if listeners_match:
            try:
                listeners = int(listeners_match.group('listeners'))
            except (ValueError, TypeError):
                listeners = None
        
        # For old Shoutcast HTML, song info might be in different fields
        # This is a simplified implementation
        return StationNowPlayingData(
            current_song=None,  # Would need more specific parsing
            listeners=listeners,
            raw_data=[parsed_data]
        )
    
    def _parse_shoutcast_html(self, html_content: str) -> Dict[str, str]:
        """Parse Shoutcast HTML content using regex"""
        regex = re.compile(
            r'<tr><td width=100 nowrap><font class=default>(?P<param_data>[a-zA-Z\s]+): </font></td>'
            r'<td><font class=default><b>(?P<param_value>.*?)</b></td></tr>',
            re.IGNORECASE | re.MULTILINE
        )
        
        data = {}
        for match in regex.finditer(html_content):
            param_data = match.group('param_data')
            value = match.group('param_value')
            if param_data:
                data[param_data] = value
        
        return data


class AripiSpreCerScraper(BaseScraper):
    """Scraper for Aripi spre Cer API"""
    
    def get_scraper_type(self) -> str:
        return "aripisprecer_api"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from Aripi spre Cer JSON response"""
        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        song_name = response_data.get("title")
        artist = response_data.get("artist")
        picture = response_data.get("picture")
        
        # Clean picture URL
        thumbnail_url = picture if picture and picture != "" else None
        
        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            thumbnail_url=thumbnail_url
        )
        
        return StationNowPlayingData(
            current_song=song_data,
            listeners=None,  # API doesn't provide listener count
            raw_data=[response_data]
        )


class RadioFiladelfiaScraper(BaseScraper):
    """Scraper for Radio Filadelfia API"""
    
    def get_scraper_type(self) -> str:
        return "radio_filadelfia_api"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from Radio Filadelfia JSON response"""
        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        song_name = response_data.get("Title")
        artist = response_data.get("Artist")
        picture = response_data.get("Picture")
        
        # Build thumbnail URL
        thumbnail_url = None
        if picture and picture != "":
            thumbnail_url = f"https://asculta.radiofiladelfia.ro:8500/meta/albumart/{picture}"
        
        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            thumbnail_url=thumbnail_url
        )
        
        return StationNowPlayingData(
            current_song=song_data,
            listeners=None,  # API doesn't provide listener count
            raw_data=[response_data]
        )


class SonicPanelScraper(BaseScraper):
    """Scraper for SonicPanel API"""
    
    def get_scraper_type(self) -> str:
        return "sonicpanel"
    
    def extract_data(self, response_data: Any) -> StationNowPlayingData:
        """Extract data from SonicPanel JSON response"""
        if not isinstance(response_data, dict):
            return StationNowPlayingData(current_song=None, listeners=None)
        
        raw_title = response_data.get("title", "")
        song_name, artist = DataFormatter.parse_title_artist(raw_title)
        
        song_data = self._create_song_data(
            name=song_name,
            artist=artist,
            raw_title=raw_title
            # Note: thumbnail from 'art' field doesn't work reliably per original comment
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