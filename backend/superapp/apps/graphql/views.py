import json
import logging
from os import environ

import requests
from django.http import HttpRequest, HttpResponse
from strawberry.django.views import GraphQLView
from strawberry.http import GraphQLHTTPResponse
from strawberry.types import ExecutionResult

from superapp.apps.posthog_error_tracking.utils import track_event

logger = logging.getLogger(__name__)


class GraphQLProxyView(GraphQLView):
    """
    GraphQL proxy that extends Strawberry's GraphQLView and falls back to Hasura on error
    """

    def get_hasura_url(self):
        """Get Hasura URL from environment variable"""
        return environ.get('ADMIN_HASURA_GRAPHQL_URL', '')

    def log_error_to_posthog(self, error_type, query, error_message, url):
        """Log error to PostHog with query details"""
        try:
            properties = {
                'error_type': error_type,
                'graphql_query': query,
                'error_message': str(error_message),
                'failed_url': url,
                'proxy_version': 'v1'
            }
            track_event('anonymous', 'graphql_proxy_error', properties)
        except Exception as e:
            logger.error(f"Failed to log to PostHog: {str(e)}")

    def should_fallback_to_hasura(self, result: ExecutionResult) -> bool:
        """Determine if we should fallback to Hasura based on errors"""
        if not result.errors:
            return False

        # Check for critical errors that warrant fallback
        critical_error_keywords = [
            'field',  # Field not found, might exist in Hasura
            'type',   # Type not found, might exist in Hasura
            'query',  # Query parsing errors
            'schema', # Schema-related errors
            'resolver', # Resolver errors
        ]
        
        for error in result.errors:
            error_message = str(error).lower()
            if any(keyword in error_message for keyword in critical_error_keywords):
                return True
                
        return False

    def attempt_hasura_fallback(self, request: HttpRequest) -> GraphQLHTTPResponse:
        """Attempt to forward request to Hasura"""
        try:
            # Get request data
            if hasattr(request, '_body'):
                request_body = request._body
            else:
                request_body = request.body
                
            request_data = json.loads(request_body) if request_body else {}
            query = request_data.get('query', '')

            # Prepare headers for Hasura
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Forward auth headers if present
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header:
                headers['Authorization'] = auth_header

            # Make request to Hasura
            hasura_url = self.get_hasura_url()
            response = requests.post(
                hasura_url,
                json=request_data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    hasura_data = response.json()
                    logger.info(f"Successfully fell back to Hasura for query: {query[:100]}...")
                    return hasura_data
                except json.JSONDecodeError:
                    self.log_error_to_posthog('hasura_json_decode_error', query, 'Invalid JSON response', hasura_url)
                    
            else:
                self.log_error_to_posthog('hasura_http_error', query, f"HTTP {response.status_code}", hasura_url)

        except requests.RequestException as e:
            query = request_data.get('query', '') if 'request_data' in locals() else ''
            self.log_error_to_posthog('hasura_connection_error', query, str(e), self.get_hasura_url())
            logger.error(f"Hasura fallback failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during Hasura fallback: {str(e)}")

        return None

    def process_result(self, request: HttpRequest, result: ExecutionResult) -> GraphQLHTTPResponse:
        """Process GraphQL result with Hasura fallback on errors"""
        
        # Check if we should attempt Hasura fallback
        if self.should_fallback_to_hasura(result):
            # Extract query for logging
            try:
                request_data = json.loads(request.body) if request.body else {}
                query = request_data.get('query', '')
            except:
                query = ''

            # Log the errors that triggered fallback
            for error in result.errors:
                self.log_error_to_posthog('strawberry_error', query, str(error), 'local_strawberry')
                logger.warning(f"GraphQL error triggering Hasura fallback: {error}")

            # Attempt Hasura fallback
            hasura_response = self.attempt_hasura_fallback(request)
            if hasura_response:
                logger.info("Successfully used Hasura fallback")
                return hasura_response

            # If fallback fails, log additional error
            self.log_error_to_posthog('fallback_failed', query, 'Both Strawberry and Hasura failed', '')
            logger.error("Both Strawberry GraphQL and Hasura fallback failed")

        # Standard response processing (either no errors or fallback failed)
        data: GraphQLHTTPResponse = {"data": result.data}
        
        if result.errors:
            data["errors"] = [err.formatted for err in result.errors]
            # Log remaining errors
            for error in result.errors:
                logger.error(f"GraphQL Error (no fallback): {error}")

        return data
