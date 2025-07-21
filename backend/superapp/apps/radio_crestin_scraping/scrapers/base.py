import ssl
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from django.conf import settings

from ..utils.data_types import StationNowPlayingData, SongData
from ..utils.formatters import DataFormatter


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all radio station scrapers"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # Create SSL context that doesn't verify certificates
        # (matching the old backend's rejectUnauthorized: false)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    @abstractmethod
    def get_scraper_type(self) -> str:
        """Return the scraper type identifier"""
        pass

    @abstractmethod
    def extract_data(self, response_data: Any, config=None) -> StationNowPlayingData:
        """Extract and format data from the API response"""
        pass

    async def scrape(self, url: str, config=None, **kwargs) -> StationNowPlayingData:
        """Main scraping method"""
        logger.info(f"Scraping {self.get_scraper_type()} from: {url}")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=False  # Disable SSL verification
            ) as client:
                response = await self._make_request(client, url, **kwargs)
                data = await self._process_response(response)
                result = self.extract_data(data, config)
                return DataFormatter.format_station_data(result)

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error scraping {url}: {error}")
            return StationNowPlayingData(
                timestamp=datetime.now().isoformat(),
                current_song=None,
                listeners=None,
                error=[self._serialize_error(error)]
            )

    async def _make_request(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with appropriate headers"""
        headers = self._get_default_headers()
        headers.update(kwargs.get('headers', {}))

        method = kwargs.get('method', 'GET')

        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            **{k: v for k, v in kwargs.items() if k not in ['headers', 'method']}
        )
        response.raise_for_status()
        return response

    async def _process_response(self, response: httpx.Response) -> Any:
        """Process the HTTP response and return appropriate data"""
        content_type = response.headers.get('content-type', '').lower()

        if 'application/json' in content_type:
            return response.json()
        elif 'text/' in content_type or 'application/xml' in content_type:
            return response.text
        else:
            return response.content

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests"""
        return {
            'User-Agent': 'RadioCrestin/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
            'Upgrade-Insecure-Requests': '1',
        }

    def _serialize_error(self, error: Exception) -> Dict[str, Any]:
        """Serialize error for storage"""
        return {
            'type': type(error).__name__,
            'message': str(error),
            'timestamp': datetime.now().isoformat()
        }

    def _create_song_data(self, name: Optional[str] = None,
                         artist: Optional[str] = None,
                         thumbnail_url: Optional[str] = None,
                         raw_title: Optional[str] = None) -> Optional[SongData]:
        """Helper method to create SongData object"""
        if not any([name, artist, raw_title]):
            return None

        return SongData(
            name=name,
            artist=artist,
            thumbnail_url=thumbnail_url,
            raw_title=raw_title
        )
