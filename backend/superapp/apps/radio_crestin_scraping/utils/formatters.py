import re
import urllib.parse
from typing import Optional
from .data_types import StationNowPlayingData, SongData


class DataFormatter:
    """Utility class for formatting and cleaning scraped data"""
    
    ALLOWED_CHARACTERS_PATTERN = re.compile(r'[^a-zA-ZÀ-žaâăáeéèiîoóöőøsșşșştțţțţ\-\s?\'&]')
    UNICODE_DECODE_PATTERN = re.compile(r'&#(\d+);')
    
    @staticmethod
    def clean_song_text(text: Optional[str]) -> Optional[str]:
        """Clean and format song title or artist name"""
        if not text or text == "undefined" or len(text) <= 2:
            return None
            
        # Decode Unicode special chars
        text = DataFormatter.UNICODE_DECODE_PATTERN.sub(
            lambda m: chr(int(m.group(1))), text
        )
        
        # Basic cleaning
        text = (text
                .replace("_", " ")
                .replace("  ", " ")
                .replace("undefined", "")
                .strip())
        
        # Remove special characters
        text = DataFormatter.ALLOWED_CHARACTERS_PATTERN.sub("", text)
        
        # Capitalize first letter
        if text and len(text) > 0:
            text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Remove leading/trailing dashes
        text = re.sub(r'^-+|-+$', '', text).strip()
        
        # Decode URL-encoded characters
        try:
            text = urllib.parse.unquote(text)
        except Exception:
            pass
            
        return text if text and len(text) >= 2 else None
    
    @staticmethod
    def parse_title_artist(raw_title: str) -> tuple[Optional[str], Optional[str]]:
        """Parse raw title into song name and artist"""
        if not raw_title:
            return None, None
            
        parts = raw_title.split(" - ", 1)
        
        if len(parts) == 2:
            artist = DataFormatter.clean_song_text(parts[0])
            song_name = DataFormatter.clean_song_text(parts[1])
        else:
            song_name = DataFormatter.clean_song_text(parts[0])
            artist = None
            
        return song_name, artist
    
    @staticmethod
    def format_station_data(data: StationNowPlayingData) -> StationNowPlayingData:
        """Format and clean station now playing data"""
        if not data.current_song:
            return data
            
        song = data.current_song
        
        # Clean existing fields
        if song.name:
            song.name = DataFormatter.clean_song_text(song.name)
        if song.artist:
            song.artist = DataFormatter.clean_song_text(song.artist)
        if song.thumbnail_url and (not song.thumbnail_url or 
                                 song.thumbnail_url == "undefined" or 
                                 len(song.thumbnail_url) < 2):
            song.thumbnail_url = None
            
        # If we have a raw_title but no parsed name/artist, try to parse it
        if song.raw_title and not song.name:
            song_name, artist = DataFormatter.parse_title_artist(song.raw_title)
            if song_name:
                song.name = song_name
            if artist:
                song.artist = artist
                
        # Fallback logic from original code
        if not song.name or len(song.name) < 2:
            song.name = song.artist or song.raw_title
            song.artist = None
            
        if not song.name:
            song.name = song.raw_title
            song.artist = None
            
        # Final cleanup
        if song.name:
            song.name = DataFormatter.clean_song_text(song.name)
        if song.artist:
            song.artist = DataFormatter.clean_song_text(song.artist)
            
        return data