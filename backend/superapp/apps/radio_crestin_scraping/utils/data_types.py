from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SongData:
    """Data structure for song information"""
    raw_title: Optional[str] = None
    name: Optional[str] = None
    artist: Optional[str] = None
    thumbnail_url: Optional[str] = None


@dataclass
class StationNowPlayingData:
    """Data structure for station now playing information"""
    timestamp: Optional[str] = None
    current_song: Optional[SongData] = None
    listeners: Optional[int] = None
    raw_data: List[Dict[str, Any]] = None
    error: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.raw_data is None:
            self.raw_data = []
        if self.error is None:
            self.error = []


@dataclass
class StationUptimeData:
    """Data structure for station uptime information"""
    timestamp: str
    is_up: bool
    latency_ms: int
    raw_data: List[Dict[str, Any]]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RssFeedPost:
    """Data structure for RSS feed post"""
    title: str
    link: str
    description: str
    published: str


@dataclass
class StationRssFeedData:
    """Data structure for station RSS feed data"""
    posts: List[RssFeedPost] = None
    
    def __post_init__(self):
        if self.posts is None:
            self.posts = []