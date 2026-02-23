"""
REST API endpoint definitions for radio_crestin app

This module defines REST API endpoints that are backed by GraphQL queries/mutations.
"""

import json
from django.utils import timezone
from typing import Dict, Any, Optional

from superapp.apps.graphql.rest_api import RestApiEndpoint, HttpMethod
from ..constants import STATIONS_GRAPHQL_QUERY, REVIEWS_GRAPHQL_QUERY
from .constants_metadata import STATIONS_METADATA_GRAPHQL_QUERY, STATIONS_METADATA_HISTORY_GRAPHQL_QUERY


def validate_timestamp_not_future(request) -> Optional[Dict[str, Any]]:
    """
    Validate that the timestamp parameter is not in the future (beyond current time + 2 seconds).

    This prevents CDN caches from caching responses for timestamps that don't exist yet.

    Returns:
        None if valid, error dict if timestamp is too far in the future
    """
    timestamp_param = request.GET.get('timestamp') or request.GET.get('_t')
    if timestamp_param:
        try:
            timestamp_value = int(timestamp_param)
            current_timestamp = timezone.now().timestamp()
            max_allowed_timestamp = current_timestamp + 2  # Allow 2 seconds of clock drift

            if timestamp_value > max_allowed_timestamp:
                return {
                    'error': 'Timestamp is in the future. Please use a valid timestamp.',
                    'status': 400
                }
        except (ValueError, TypeError):
            return {
                'error': 'Invalid timestamp format. Please provide a valid integer timestamp.',
                'status': 400
            }
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
    cache_control = "public, max-age=0, s-maxage=14400, immutable"
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
    cache_control = "public, max-age=0, s-maxage=14400, immutable"
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
    cache_control = "public, max-age=0, s-maxage=30, stale-while-revalidate=30"
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
        variables = {}
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
    cache_control = "public, max-age=0, s-maxage=60"
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


# List of endpoint classes to register
REST_ENDPOINTS = [
    StationsApiEndpoint,
    StationsMetadataApiEndpoint,
    StationsMetadataHistoryApiEndpoint,
    ShareLinksApiEndpoint,
    ReviewsApiEndpoint,
    ReviewsListApiEndpoint,
]
