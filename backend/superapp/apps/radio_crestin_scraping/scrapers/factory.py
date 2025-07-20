from typing import Dict, Type, Optional

from .base import BaseScraper
from .shoutcast import ShoutcastScraper
from .icecast import IcecastScraper
from .radio_co import RadioCoScraper
from .shoutcast_xml import ShoutcastXmlScraper
from .stream_id3 import StreamId3Scraper
from .html_scrapers import (
    OldIcecastHtmlScraper, OldShoutcastHtmlScraper,
    AripiSpreCerScraper, RadioFiladelfiaScraper, SonicPanelScraper
)


class ScraperFactory:
    """Factory class for creating appropriate scrapers based on category slug"""
    
    _scrapers: Dict[str, Type[BaseScraper]] = {
        'shoutcast': ShoutcastScraper,
        'icecast': IcecastScraper,
        'radio_co': RadioCoScraper,
        'shoutcast_xml': ShoutcastXmlScraper,
        'stream_id3': StreamId3Scraper,
        'old_icecast_html': OldIcecastHtmlScraper,
        'old_shoutcast_html': OldShoutcastHtmlScraper,
        'aripisprecer_api': AripiSpreCerScraper,
        'radio_filadelfia_api': RadioFiladelfiaScraper,
        'sonicpanel': SonicPanelScraper,
    }
    
    @classmethod
    def get_scraper(cls, category_slug: str, **kwargs) -> Optional[BaseScraper]:
        """Get a scraper instance for the given category slug"""
        scraper_class = cls._scrapers.get(category_slug)
        if scraper_class:
            return scraper_class(**kwargs)
        return None
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported scraper types"""
        return list(cls._scrapers.keys())
    
    @classmethod
    def register_scraper(cls, category_slug: str, scraper_class: Type[BaseScraper]):
        """Register a new scraper type"""
        cls._scrapers[category_slug] = scraper_class
    
    @classmethod
    def is_supported(cls, category_slug: str) -> bool:
        """Check if a scraper type is supported"""
        return category_slug in cls._scrapers