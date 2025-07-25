# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radio Crestin Backend is a **Christian Radio Stations Directory** system providing:
- Radio station management and streaming
- HLS (HTTP Live Streaming) conversion service  
- Real-time metadata scraping from radio stations
- GraphQL API with Hasura integration
- Admin portal for station management
- Analytics and listener tracking

## Tech Stack

**Backend:** Django 5.1 with SuperApp architecture, PostgreSQL (TimescaleDB), Redis, Celery
**API:** Hasura GraphQL Engine (v2.33.4) + Django GraphQL integration
**Frontend:** Django Admin with django-unfold theme, TailwindCSS + Flowbite, Alpine.js
**Streaming:** NGINX + FFmpeg for HLS conversion
**Infrastructure:** Docker, Kubernetes, S3-compatible storage

## Development Setup

```bash
# Quick setup
cp .env.local.example .env.local
cp .env.example .env
make start-docker
sleep 10s
make fresh-install
```

## Essential Commands

### Docker Operations
```bash
make start-docker              # Start all services
make force-start-docker        # Force recreate containers
make stop-docker              # Stop all services
make destroy-docker           # Stop and remove volumes
make web-bash                 # Access Django container
make web-logs                 # View Django logs
make hls-streaming-logs       # View HLS service logs
```

### Database Operations
```bash
make makemigrations           # Create new migrations
make migrate                  # Apply migrations
make createsuperuser          # Create admin user
make sync-prod-db-clean       # Sync production data locally (CAUTION)
```

### Development Tools
```bash
make start-tailwind-watch     # Watch TailwindCSS changes for admin
make run-all-scrapers         # Test metadata scraping functionality
make collectstatic            # Collect static files
```

### Testing and Quality
```bash
# Run tests (check specific app test patterns)
docker-compose run web python manage.py test
# Run linting (check if linting tools are configured)
docker-compose run web python manage.py check
```

## Architecture

### Django SuperApp Structure
```
backend/superapp/apps/
   radio_crestin/           # Core models (stations, artists, songs)
   radio_crestin_scraping/  # Metadata scraping system
   admin_portal/            # Enhanced admin interface
   authentication/         # User management with django-allauth
   graphql/                # GraphQL schema & resolvers
   tasks/                  # Celery background tasks
   backups/                # Database backup functionality
```

### Key Services
- **Django Backend** (port 8080): Main application server
- **PostgreSQL** (port 5432): TimescaleDB database
- **Redis** (port 6379): Caching and Celery message broker
- **Hasura GraphQL** (port 8081): GraphQL API engine
- **HLS Streaming** (port 8082): Stream conversion service

## Coding Conventions

### File Organization
- **Admins**: `superapp/apps/<app_name>/admin/<model_name_slug>.py`
- **Models**: `superapp/apps/<app_name>/models/<model_name_slug>.py`  
- **Services**: `superapp/apps/<app_name>/services/<service_name>.py`
- **Tasks**: `superapp/apps/<app_name>/tasks/<task_name>.py`
- **Views**: `superapp/apps/<app_name>/views/<view_name>.py`
- **Signals**: `superapp/apps/<app_name>/signals/<model_name_slug>.py`

### Django Guidelines
- Follow PEP 8 compliance and Django best practices
- Use Django ORM, avoid raw SQL queries
- Use `django-unfold` with `SuperAppModelAdmin` for admin
- Register with `superapp_admin_site` from `superapp.apps.admin_portal.sites`
- Prefer `autocomplete_fields` for ForeignKey/ManyToMany relationships
- All user-facing strings must use Django i18n: `_('Text')`

### Services Pattern
- Keep services with just two operations: `upsert` and `delete`
- All database interactions should go through services layer
- Services handle business logic, views handle request/response

### Admin Integration
```python
# Example admin registration
from superapp.apps.admin_portal.admin import SuperAppModelAdmin
from superapp.apps.admin_portal.sites import superapp_admin_site

@admin.register(MyModel, site=superapp_admin_site)
class MyModelAdmin(SuperAppModelAdmin):
    list_display = ['slug', 'name', 'created_at']
    search_fields = ['name', 'slug']
    autocomplete_fields = ['related_field']
```

### SuperApp Configuration
Each app configures itself in `settings.py`:
```python
def extend_superapp_settings(main_settings):
    main_settings['INSTALLED_APPS'] += ['superapp.apps.my_app']
    # Add navigation, middleware, etc.
```

## Environment Configuration

- **`.env`**: Main environment configuration
- **`backend/.env.local`**: Local development overrides
- **`backend_hasura/.env`**: Hasura-specific settings

## Testing Patterns

Test scraping functionality:
```bash
make run-all-scrapers
```

## Deployment

The project uses Kubernetes with Skaffold for deployment. Configuration is in `/deploy/` with:
- Component-based architecture
- Git-crypt for secrets management
- Multiple environment support
- Certificate management with cert-manager

## Mobile Responsiveness

All frontend components should be mobile responsive using TailwindCSS classes and responsive design patterns.

## Important Notes

- **Commit frequently**: Make granular commits after each task completion
- **Services pattern**: Use only upsert/delete operations in services
- **SuperApp structure**: Follow the modular app architecture
- **Mobile first**: Ensure all UI components are responsive
- **i18n support**: Use Django translation for all user-facing text
- **Security**: Never commit secrets; use environment variables
