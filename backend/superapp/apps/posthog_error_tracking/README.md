# PostHog Error Tracking App

This Django superapp integrates PostHog analytics and error tracking into the application using the official PostHog Django SDK.

## Features

- **Automatic Error Tracking**: Captures all unhandled exceptions with full context
- **Global HTTP Error Handlers**: Custom handlers for 404, 500, 403, and 400 errors that track to PostHog
- **User Context**: Automatically associates errors with authenticated users
- **Session Tracking**: Tracks user sessions and request metadata
- **Admin Integration**: Adds PostHog dashboard links to Django admin sidebar

## Configuration

Add the following environment variables to your `.env` file:

```bash
POSTHOG_API_KEY=your_posthog_api_key
POSTHOG_HOST=https://eu.i.posthog.com
```

## Usage

### Manual Event Tracking

```python
from superapp.apps.posthog_error_tracking import track_event

# Track custom events
track_event('user-123', 'station_played', {
    'station_id': 'station-456',
    'station_name': 'Radio Station Name',
    'duration': 300
})

# Track user events
from superapp.apps.posthog_error_tracking import track_user_login, track_user_signup

track_user_login(user)
track_user_signup(user)
```

### Manual Error Tracking

```python
from superapp.apps.posthog_error_tracking import track_error

# Track custom errors
track_error(
    request,
    error_type='ValidationError',
    error_message='Invalid input provided',
    status_code=400,
    exception=exception  # optional
)
```

### Testing

Test the PostHog integration using the management command:

```bash
# Test all features
docker-compose exec web python manage.py test_posthog_tracking --test-all

# Test only events
docker-compose exec web python manage.py test_posthog_tracking --test-events

# Test only errors
docker-compose exec web python manage.py test_posthog_tracking --test-errors
```

## How It Works

1. **PostHog Middleware**: The official `PosthogContextMiddleware` automatically:
   - Extracts session and user information from requests
   - Tags all events with relevant metadata via `POSTHOG_MW_EXTRA_TAGS`
   - Captures exceptions automatically with full user context

2. **User Tagging**: Custom `add_user_tags()` function enriches all PostHog events with:
   - User ID, email, username
   - Staff/superuser status
   - Authentication state
   - User profile information (first_name, last_name, date_joined)

3. **Global Error Handlers**: Custom Django error handlers that:
   - Capture HTTP errors (404, 500, etc.)
   - Extract user and request context
   - Send detailed error information to PostHog

4. **Superapp Integration**: Follows the superapp pattern:
   - Automatically registers with Django via `extend_superapp_settings()`
   - Adds required middleware and configuration
   - Integrates with admin interface

## Admin Interface

When configured, the app adds PostHog-related links to the Django admin sidebar:
- Error Tracking Dashboard
- Analytics Dashboard

These links point directly to your PostHog instance for easy access to error reports and analytics.