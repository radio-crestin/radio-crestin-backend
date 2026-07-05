"""
REST API endpoint definitions for radio_crestin app

This module defines REST API endpoints that are backed by GraphQL queries/mutations.
"""

import json
from django.utils import timezone
from typing import Dict, Any, Optional

from superapp.apps.graphql.rest_api import RestApiEndpoint, HttpMethod
from ..constants import (
    STATIONS_GRAPHQL_QUERY,
    REVIEWS_GRAPHQL_QUERY,
    STATION_PLAYLIST_GRAPHQL_QUERY,
    PRIVATE_STATIONS_GRAPHQL_QUERY,
)
from .constants_metadata import STATIONS_METADATA_GRAPHQL_QUERY, STATIONS_METADATA_HISTORY_GRAPHQL_QUERY


def rounded_timestamp(window_seconds: int = 10) -> int:
    """Current unix timestamp rounded down to a multiple of `window_seconds`.

    Timestamped endpoints redirect to `?timestamp=<rounded>` so the URL is
    stable within a window and safe to cache. Most endpoints use the default
    10-second window; pass a smaller window for faster-polling endpoints.
    """
    return int(timezone.now().timestamp() // window_seconds) * window_seconds


def parse_slug_filters(request) -> Dict[str, Any]:
    """Parse station_slugs and exclude_station_slugs from comma-separated query params."""
    variables = {}
    slugs = request.GET.get('station_slugs')
    if slugs:
        variables['station_slugs'] = [s.strip() for s in slugs.split(',') if s.strip()]
    exclude = request.GET.get('exclude_station_slugs')
    if exclude:
        variables['exclude_station_slugs'] = [s.strip() for s in exclude.split(',') if s.strip()]
    return variables


def validate_timestamp_not_future(request, window_seconds: int = 10) -> Optional[Dict[str, Any]]:
    """
    Validate that the timestamp parameter is not in the future (beyond current time + 2 seconds).

    If the timestamp is invalid or in the future (e.g. client clock skew), redirect to
    the correct rounded timestamp instead of returning an error.

    Args:
        request: Django request object
        window_seconds: Rounding window used for the corrected redirect timestamp

    Returns:
        None if valid, redirect dict if timestamp needs correction
    """
    timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')
    if timestamp_param:
        current_timestamp = timezone.now().timestamp()
        needs_redirect = False

        try:
            timestamp_value = int(timestamp_param)
            max_allowed_timestamp = current_timestamp + 2  # Allow 2 seconds of clock drift
            if timestamp_value > max_allowed_timestamp:
                needs_redirect = True
        except (ValueError, TypeError):
            needs_redirect = True

        if needs_redirect:
            # Build redirect URL replacing the bad timestamp with the correct one
            query_params = dict(request.GET)
            query_params.pop('timestamp', None)
            query_params.pop('_t', None)
            query_params['timestamp'] = [str(rounded_timestamp(window_seconds))]
            query_string = '&'.join(
                f"{k}={v[0] if isinstance(v, list) else v}" for k, v in query_params.items()
            )
            return {'redirect': f"{request.path}?{query_string}"}
    return None


class StationsApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for stations list

    Provides stations data with timestamp-based cache control.
    """

    path = "api/v1/stations"
    graphql_query = STATIONS_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_stations"
    cache_control = "public, max-age=2592000, immutable"
    cors_enabled = True

    @staticmethod
    def pre_processor(request, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Add timestamp redirect for cache control and validate timestamp is not in the future.

        Redirects to a timestamped URL if timestamp parameter is not present.
        This helps with caching and ensures fresh data every 10 seconds.
        """
        # Get current timestamp rounded to 10 seconds
        current_timestamp = timezone.now().timestamp()
        rounded_timestamp = int(current_timestamp // 10) * 10

        # Check if we already have the timestamp parameter
        timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')

        if not timestamp_param:
            # Return redirect response
            redirect_url = f"{request.path}?timestamp={rounded_timestamp}"
            return {'redirect': redirect_url}

        # Validate timestamp is not in the future
        validation_error = validate_timestamp_not_future(request)
        if validation_error:
            return validation_error

        # No redirect needed
        return None

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        return parse_slug_filters(request)


class ShareLinksApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for share links

    Handles share link creation and retrieval for anonymous users.
    """

    path = "api/v1/share-links/<str:anonymous_id>/"
    name = "api_v1_share_links"
    method = HttpMethod.GET
    cache_control = "no-cache"
    cors_enabled = True

    # GraphQL mutation for share links
    graphql_query = """
    mutation GetShareLink($anonymous_id: String!) {
      get_share_link(anonymous_id: $anonymous_id) {
        __typename
        ... on GetShareLinkResponse {
          anonymous_id
          message
          share_link {
            visit_count
            url
            share_id
            is_active
            created_at
            share_message
            share_section_message
            share_section_title
            share_station_message
          }
          success
        }
        ... on OperationInfo {
          __typename
          messages {
            code
            field
            kind
            message
          }
        }
      }
    }
    """

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        """
        Extract GraphQL variables from request

        Args:
            request: Django request object
            **kwargs: URL parameters

        Returns:
            Dict with GraphQL variables
        """
        # Extract anonymous_id from URL kwargs
        anonymous_id = kwargs.get('anonymous_id', '')

        return {
            'anonymous_id': anonymous_id
        }


class ReviewsApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for submitting station reviews.

    POST /api/v1/reviews/
    Body: { "station_id": int, "stars": int, "message": string?, "user_identifier": string? }

    Reviews are unique per IP address and station. If the same IP submits
    another review for the same station, the existing review is updated.
    """

    path = "api/v1/reviews/"
    name = "api_v1_reviews"
    method = HttpMethod.POST
    cache_control = "no-cache"
    cors_enabled = True

    # GraphQL mutation for submitting reviews
    graphql_query = """
    mutation SubmitReview($input: SubmitReviewInput!) {
      submit_review(input: $input) {
        __typename
        ... on SubmitReviewResponse {
          success
          message
          created
          review {
            id
            station_id
            song_id
            stars
            message
            user_identifier
            created_at
            updated_at
            verified
          }
        }
        ... on OperationInfo {
          __typename
          messages {
            code
            field
            kind
            message
          }
        }
      }
    }
    """

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        """
        Extract GraphQL variables from request body.

        Args:
            request: Django request object
            **kwargs: URL parameters

        Returns:
            Dict with GraphQL variables
        """
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}

        input_vars = {
            'stars': body.get('stars'),
            'message': body.get('message'),
            'user_identifier': body.get('user_identifier'),
        }
        if body.get('station_id'):
            input_vars['station_id'] = body.get('station_id')
        if body.get('station_slug'):
            input_vars['station_slug'] = body.get('station_slug')
        if body.get('song_id'):
            input_vars['song_id'] = body.get('song_id')
        return {'input': input_vars}


class DeleteReviewApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for deleting a review.

    DELETE /api/v1/reviews/delete/
    Body: { "station_id": int?, "station_slug": string?, "song_id": int? }

    Deletes the review matching the caller's IP + station + optional song.
    """

    path = "api/v1/reviews/delete/"
    name = "api_v1_reviews_delete"
    method = HttpMethod.POST
    cache_control = "no-cache"
    cors_enabled = True

    graphql_query = """
    mutation DeleteReview($input: DeleteReviewInput!) {
      delete_review(input: $input) {
        __typename
        ... on DeleteReviewResponse {
          success
          message
        }
        ... on OperationInfo {
          __typename
          messages {
            code
            field
            kind
            message
          }
        }
      }
    }
    """

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}

        input_vars: Dict[str, Any] = {}
        if body.get('station_id'):
            input_vars['station_id'] = body.get('station_id')
        if body.get('station_slug'):
            input_vars['station_slug'] = body.get('station_slug')
        if body.get('song_id'):
            input_vars['song_id'] = body.get('song_id')
        return {'input': input_vars}


class ReviewsListApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for listing station reviews.

    GET /api/v1/reviews?station_id=<id>&timestamp=<timestamp>

    Returns verified reviews for all stations or a specific station if station_id is provided.
    Uses the same timestamp-based cache control as the stations endpoint.
    """

    path = "api/v1/reviews"
    graphql_query = REVIEWS_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_reviews_list"
    cache_control = "public, max-age=2592000, immutable"
    cors_enabled = True

    @staticmethod
    def pre_processor(request, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Add timestamp redirect for cache control and validate timestamp is not in the future.

        Redirects to a timestamped URL if timestamp parameter is not present.
        This helps with caching and ensures fresh data every 10 seconds.
        """
        # Get current timestamp rounded to 10 seconds
        current_timestamp = timezone.now().timestamp()
        rounded_timestamp = int(current_timestamp // 10) * 10

        # Check if we already have the timestamp parameter
        timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')

        if not timestamp_param:
            # Build redirect URL preserving other query parameters
            query_params = dict(request.GET)
            query_params['timestamp'] = [str(rounded_timestamp)]

            # Build query string
            query_string = '&'.join(
                f"{k}={v[0]}" for k, v in query_params.items()
            )
            redirect_url = f"{request.path}?{query_string}"
            return {'redirect': redirect_url}

        # Validate timestamp is not in the future
        validation_error = validate_timestamp_not_future(request)
        if validation_error:
            return validation_error

        # No redirect needed
        return None

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        """
        Extract GraphQL variables from query parameters.

        Args:
            request: Django request object
            **kwargs: URL parameters

        Returns:
            Dict with GraphQL variables
        """
        station_id = request.GET.get('station_id')
        station_slug = request.GET.get('station_slug')

        variables = {}
        if station_id:
            try:
                variables['station_id'] = int(station_id)
            except (ValueError, TypeError):
                pass
        elif station_slug:
            variables['station_slug'] = station_slug

        return variables


class StationsMetadataApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for lightweight station metadata (uptime + now_playing).

    Supports historical lookups via timestamp and change detection via changes_from_timestamp.
    """

    path = "api/v1/stations-metadata"
    graphql_query = STATIONS_METADATA_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_stations_metadata"
    cache_control = "public, max-age=2592000, immutable"
    cors_enabled = True

    @staticmethod
    def pre_processor(request, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Add timestamp redirect for cache control and validate timestamp is not in the future.
        Preserves changes_from_timestamp in redirect.
        """
        current_timestamp = timezone.now().timestamp()
        rounded_timestamp = int(current_timestamp // 10) * 10

        timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')

        if not timestamp_param:
            # Build redirect URL preserving other query parameters
            query_params = dict(request.GET)
            query_params['timestamp'] = [str(rounded_timestamp)]
            query_string = '&'.join(
                f"{k}={v[0]}" for k, v in query_params.items()
            )
            redirect_url = f"{request.path}?{query_string}"
            return {'redirect': redirect_url}

        # Validate timestamp is not in the future
        validation_error = validate_timestamp_not_future(request)
        if validation_error:
            return validation_error

        return None

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        variables = parse_slug_filters(request)
        changes_from = request.GET.get('changes_from_timestamp')
        if changes_from:
            try:
                variables['changes_from_timestamp'] = int(changes_from)
            except (ValueError, TypeError):
                pass
        timestamp = request.GET.get('timestamp') or request.GET.get('_t')
        if timestamp:
            try:
                variables['timestamp'] = int(timestamp)
            except (ValueError, TypeError):
                pass
        return variables


class StationsMetadataHistoryApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for per-station metadata history in a time range (max 24h).
    """

    path = "api/v1/stations-metadata-history"
    graphql_query = STATIONS_METADATA_HISTORY_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_stations_metadata_history"
    cache_control = "public, max-age=60"
    cors_enabled = True

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        variables = {
            'station_slug': request.GET.get('station_slug', ''),
        }
        from_ts = request.GET.get('from_timestamp')
        if from_ts:
            variables['from_timestamp'] = int(from_ts)
        to_ts = request.GET.get('to_timestamp')
        if to_ts:
            variables['to_timestamp'] = int(to_ts)
        return variables


class StationPlaylistApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for polling a single station's managed playlist.

    GET /api/v1/station-playlist?station_slug=<slug>&timestamp=<timestamp>

    Clients poll this at a ~5-second cadence, so the timestamp is rounded to
    5-second windows (not the usual 10): each URL is unique per window, which
    makes the immutable cache header safe while still refreshing every 5s.
    """

    path = "api/v1/station-playlist"
    graphql_query = STATION_PLAYLIST_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_station_playlist"
    cache_control = "public, max-age=2592000, immutable"
    cors_enabled = True

    # 5s window to match the clients' polling cadence (other endpoints use 10s)
    TIMESTAMP_WINDOW_SECONDS = 5

    @staticmethod
    def pre_processor(request, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Add timestamp redirect for cache control and validate timestamp is not in the future.
        Preserves station_slug (and other query parameters) in the redirect.
        """
        window = StationPlaylistApiEndpoint.TIMESTAMP_WINDOW_SECONDS

        timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')

        if not timestamp_param:
            # Build redirect URL preserving other query parameters
            query_params = dict(request.GET)
            query_params['timestamp'] = [str(rounded_timestamp(window))]
            query_string = '&'.join(
                f"{k}={v[0]}" for k, v in query_params.items()
            )
            redirect_url = f"{request.path}?{query_string}"
            return {'redirect': redirect_url}

        # Validate timestamp is not in the future
        validation_error = validate_timestamp_not_future(request, window_seconds=window)
        if validation_error:
            return validation_error

        return None

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        variables: Dict[str, Any] = {}
        station_slug = request.GET.get('station_slug')
        if station_slug:
            # The stations resolver filters via the station_slugs list variable
            variables['station_slugs'] = [station_slug.strip()]
        return variables


class PrivateStationsApiEndpoint(RestApiEndpoint):
    """
    REST API endpoint for a device's private (allowlisted) stations.

    GET /api/v1/private-stations?device_id=<anonymous_id>&timestamp=<timestamp>

    Returns the same station shape as /api/v1/stations under data.stations,
    so clients merge private stations into their existing lists. Unknown
    devices get an empty list, never an error. URLs are per-device, which
    makes CDN caching mostly moot; a 60-second rounding window keeps
    device-side freshness reasonable without hammering the backend.
    """

    path = "api/v1/private-stations"
    graphql_query = PRIVATE_STATIONS_GRAPHQL_QUERY
    method = HttpMethod.GET
    name = "api_v1_private_stations"
    cache_control = "public, max-age=2592000, immutable"
    cors_enabled = True

    # 60s window: per-device URLs barely benefit from CDN caching, so a
    # larger window than the public endpoints just bounds request volume.
    TIMESTAMP_WINDOW_SECONDS = 60

    @staticmethod
    def pre_processor(request, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Add timestamp redirect for cache control and validate timestamp is not in the future.
        Preserves device_id (and other query parameters) in the redirect.
        """
        window = PrivateStationsApiEndpoint.TIMESTAMP_WINDOW_SECONDS

        timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')

        if not timestamp_param:
            # Build redirect URL preserving other query parameters
            query_params = dict(request.GET)
            query_params['timestamp'] = [str(rounded_timestamp(window))]
            query_string = '&'.join(
                f"{k}={v[0]}" for k, v in query_params.items()
            )
            redirect_url = f"{request.path}?{query_string}"
            return {'redirect': redirect_url}

        # Validate timestamp is not in the future
        validation_error = validate_timestamp_not_future(request, window_seconds=window)
        if validation_error:
            return validation_error

        return None

    @staticmethod
    def variable_extractor(request, **kwargs) -> Dict[str, Any]:
        # Empty device_id yields an empty stations list from the resolver
        return {'device_id': (request.GET.get('device_id') or '').strip()}


# List of endpoint classes to register
REST_ENDPOINTS = [
    StationsApiEndpoint,
    StationsMetadataApiEndpoint,
    StationsMetadataHistoryApiEndpoint,
    StationPlaylistApiEndpoint,
    PrivateStationsApiEndpoint,
    ShareLinksApiEndpoint,
    ReviewsApiEndpoint,
    DeleteReviewApiEndpoint,
    ReviewsListApiEndpoint,
]
