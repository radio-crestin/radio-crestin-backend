import json
import logging
from os import environ

import requests
from django.http import HttpRequest, HttpResponse
from strawberry.django.views import GraphQLView as BaseGraphQLView
from strawberry.http import GraphQLHTTPResponse
from strawberry.types import ExecutionResult

from superapp.apps.posthog_error_tracking.utils import track_event

logger = logging.getLogger(__name__)


class GraphQLProxyView(BaseGraphQLView):
    """
    GraphQL proxy that extends Strawberry's GraphQLView and falls back to Hasura on error
    """
    
    def get_context(self, request: HttpRequest, response: HttpResponse):
        """Override to ensure request and response are available in context"""
        context = super().get_context(request, response)
        # Store the request and response objects in context for access by extensions
        context["response"] = response
        context["request"] = request
        # Store the request for later use in create_response
        self._current_request = request
        return context

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

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def log_hasura_proxy_request(self, request: HttpRequest, request_data: dict, hasura_url: str):
        """Log Hasura proxy request details to PostHog"""
        try:
            properties = {
                'event_type': 'hasura_proxy_request',
                'graphql_query': request_data.get('query', ''),
                'graphql_variables': request_data.get('variables', {}),
                'graphql_operation_name': request_data.get('operationName', ''),
                'request_body': json.dumps(request_data),
                'hasura_url': hasura_url,
                'client_ip': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
                'request_method': request.method,
                'content_type': request.META.get('CONTENT_TYPE', ''),
                'has_auth': bool(request.META.get('HTTP_AUTHORIZATION')),
                'proxy_version': 'v1'
            }
            
            # Add user info if available
            if hasattr(request, 'user') and request.user.is_authenticated:
                properties['user_id'] = str(request.user.id)
                properties['user_email'] = getattr(request.user, 'email', '')
                track_event(str(request.user.id), 'graphql_hasura_proxy_request', properties)
            else:
                track_event('anonymous', 'graphql_hasura_proxy_request', properties)
                
        except Exception as e:
            logger.error(f"Failed to log Hasura proxy request to PostHog: {str(e)}")

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

            # Get Hasura URL
            hasura_url = self.get_hasura_url()
            
            # Log the proxy request to PostHog
            self.log_hasura_proxy_request(request, request_data, hasura_url)

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
            try:
                query = request_data.get('query', '') if 'request_data' in locals() else ''
            except NameError:
                query = ''
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
    
    def create_response(self, response_data: GraphQLHTTPResponse, sub_response: HttpResponse) -> HttpResponse:
        """Create the HTTP response with cache control headers if set"""
        response = super().create_response(response_data, sub_response)
        
        # Check if cache control header was set by the extension
        # Use the request we stored in get_context
        request = getattr(self, '_current_request', None)
        
        if request and hasattr(request, '_cache_control_header'):
            logger.info(f"Setting response Cache-Control header: {request._cache_control_header}")
            response['Cache-Control'] = request._cache_control_header
        else:
            logger.debug("No cache control header found on request")
        
        return response
