"""
REST API endpoint definitions for radio_crestin app

This module defines REST API endpoints that are backed by GraphQL queries/mutations.
"""

from django.utils import timezone
from typing import Dict, Any, Optional

from superapp.apps.graphql.rest_api import RestApiEndpoint, HttpMethod
from ..constants import STATIONS_GRAPHQL_QUERY


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
        Add timestamp redirect for cache control

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


# List of endpoint classes to register
REST_ENDPOINTS = [
    StationsApiEndpoint,
    ShareLinksApiEndpoint,
]
