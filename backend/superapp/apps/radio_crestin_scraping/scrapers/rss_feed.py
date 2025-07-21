import ssl
import logging
from typing import List, Optional
from datetime import datetime

import httpx
import feedparser
from django.conf import settings

from ..utils.data_types import StationRssFeedData, RssFeedPost

logger = logging.getLogger(__name__)


class RssFeedScraper:
    """Scraper for RSS feeds"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # Create SSL context that doesn't verify certificates
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def scrape_rss_feed(self, rss_url: str) -> StationRssFeedData:
        """Scrape RSS feed and return structured data"""
        if not rss_url:
            return StationRssFeedData(posts=[])

        logger.info(f"Scraping RSS feed: {rss_url}")

        try:
            # Download the RSS content
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=False  # Disable SSL verification
            ) as client:
                response = await client.get(rss_url)
                response.raise_for_status()
                rss_content = response.text

            # Parse the RSS content
            feed = feedparser.parse(rss_content)

            posts = []
            for entry in feed.entries:
                post = self._parse_rss_entry(entry)
                if post:
                    posts.append(post)

            return StationRssFeedData(posts=posts)

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error scraping RSS feed {rss_url}: {error}")
            return StationRssFeedData(posts=[])

    def _parse_rss_entry(self, entry) -> Optional[RssFeedPost]:
        """Parse a single RSS entry"""
        try:
            # Extract required fields
            title = getattr(entry, 'title', '')
            link = getattr(entry, 'link', '')
            description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')

            # Handle published date
            published = ''
            if hasattr(entry, 'published'):
                published = entry.published
            elif hasattr(entry, 'updated'):
                published = entry.updated
            elif hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6]).isoformat()

            if not title or not link:
                return None

            return RssFeedPost(
                title=title,
                link=link,
                description=description,
                published=published
            )

        except Exception as error:
            if settings.DEBUG:
                raise
            logger.error(f"Error parsing RSS entry: {error}")
            return None
