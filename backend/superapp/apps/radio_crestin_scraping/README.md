# Radio Crestin Scraping App

This Django app implements an efficient, Celery-based radio station scraping system that replaces the old Node.js backend. It provides automated scraping of radio station metadata (now playing songs, listener counts) and RSS feeds.

## Architecture

### Key Components

1. **Scrapers** (`scrapers/`):
   - Individual scraper classes for each radio platform type
   - Base scraper class with common functionality
   - Factory pattern for scraper creation
   - Async HTTP client with SSL flexibility

2. **Services** (`services/`):
   - Database operations layer with upsert/delete operations
   - Efficient bulk operations for performance
   - Transaction safety

3. **Tasks** (`tasks/`):
   - Celery tasks for async processing
   - Periodic task scheduling
   - Error handling and retries

4. **Utils** (`utils/`):
   - Data type definitions
   - Text formatting and cleaning utilities

### Supported Scraper Types

- **shoutcast**: Shoutcast JSON API
- **icecast**: Icecast JSON API  
- **radio_co**: Radio.co API
- **shoutcast_xml**: Shoutcast XML stats
- **stream_id3**: Direct stream ID3 metadata
- **old_icecast_html**: Legacy Icecast HTML pages
- **old_shoutcast_html**: Legacy Shoutcast HTML pages
- **aripisprecer_api**: Aripi spre Cer API
- **radio_filadelfia_api**: Radio Filadelfia API
- **sonicpanel**: SonicPanel API

## Features

### Efficient Database Operations
- Upsert operations for songs, artists, and station data
- Bulk operations for posts
- Foreign key management with proper conflict resolution
- Automatic cleanup of old data

### Robust Scraping
- SSL certificate flexibility (matching old backend behavior)
- Comprehensive error handling and logging
- Data formatting and cleaning (Unicode, special characters)
- Fallback logic for missing song/artist data

### Celery Integration
- Individual station tasks for parallel processing
- Periodic scheduling (every 5 min for metadata, 30 min for RSS)
- Automatic retries with exponential backoff
- Task result tracking

### Data Quality
- Text cleaning and normalization
- Artist/song title parsing from various formats
- Thumbnail URL validation
- Error tracking in database

## Installation

1. Install required dependencies:
```bash
pip install httpx feedparser
```

2. Add apps to Django settings:
```python
INSTALLED_APPS = [
    # ...
    'superapp.apps.radio_crestin_scraping',
    'superapp.apps.tasks',
]
```

3. Configure Celery settings in your Django settings:
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

## Usage

### Manual Task Execution

```python
from superapp.apps.radio_crestin_scraping.tasks.scraping_tasks import (
    scrape_station_metadata,
    scrape_station_rss_feed,
    scrape_all_stations_metadata,
    scrape_all_stations_rss_feeds
)

# Scrape single station
scrape_station_metadata.delay(station_id=1)

# Scrape all stations
scrape_all_stations_metadata.delay()
```

### Periodic Tasks

Tasks are automatically scheduled via Celery Beat:
- Station metadata: Every 5 minutes
- RSS feeds: Every 30 minutes  
- Data cleanup: Daily at 2 AM

### Adding New Scrapers

1. Create scraper class inheriting from `BaseScraper`
2. Implement `get_scraper_type()` and `extract_data()` methods
3. Register in `ScraperFactory`

Example:
```python
class MyCustomScraper(BaseScraper):
    def get_scraper_type(self) -> str:
        return "my_custom_api"
    
    def extract_data(self, response_data) -> StationNowPlayingData:
        # Implementation here
        pass

# Register in factory
ScraperFactory.register_scraper("my_custom_api", MyCustomScraper)
```

## Migration from Old Backend

This implementation provides feature parity with the old Node.js backend:

- ✅ All scraper types supported
- ✅ RSS feed processing
- ✅ Data formatting and cleaning logic
- ✅ Database upsert operations
- ✅ Error handling and logging
- ✅ Periodic execution
- ✅ SSL certificate flexibility

### Key Improvements

- **Better Architecture**: Separated concerns with clear service layers
- **Scalability**: Celery-based parallel processing
- **Maintainability**: Individual scraper files, factory pattern
- **Performance**: Bulk database operations, async HTTP clients
- **Reliability**: Transaction safety, proper error handling
- **Monitoring**: Structured logging, task result tracking

## Configuration

### Environment Variables

The scrapers inherit SSL and timeout configurations. Customize via:

```python
# In Django settings or environment
SCRAPING_TIMEOUT = 10  # seconds
SCRAPING_SSL_VERIFY = False  # matches old backend behavior
```

### Database Models

Uses existing Radio Crestin models:
- `Stations`
- `StationsNowPlaying` 
- `StationsUptime`
- `Posts`
- `Songs`
- `Artists`
- `StationsMetadataFetch`

## Monitoring

Tasks can be monitored via:
- Celery Flower dashboard
- Django admin interface  
- Application logs
- Database records with error tracking

## Performance

- Async HTTP requests for concurrent scraping
- Bulk database operations
- Efficient query patterns with select_related/prefetch_related
- Task-level parallelization via Celery
- Minimal memory footprint with streaming where possible