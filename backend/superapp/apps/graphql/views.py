import json
import logging
from os import environ

import requests
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from superapp.apps.posthog_error_tracking.utils import track_event

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class GraphQLProxyView(View):
    """
    GraphQL v1 proxy that forwards requests to v2/graphql and falls back to Hasura on failure
    """

    def get_hasura_url(self):
        """Get Hasura URL from environment variable with fallback"""
        return environ.get('ADMIN_HASURA_GRAPHQL_URL', '')

    def get_v2_url(self, request):
        """Build v2/graphql URL based on current request"""
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        return f"{scheme}://{host}/v2/graphql"

    def forward_request(self, url, data, headers, method='POST'):
        """Forward GraphQL request to specified URL with proper HTTP method"""
        try:
            method = method.upper()
            
            if method == 'GET':
                response = requests.get(
                    url,
                    params=data if isinstance(data, dict) else None,
                    headers=headers,
                    timeout=30
                )
            elif method == 'POST':
                response = requests.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
            elif method == 'HEAD':
                response = requests.head(
                    url,
                    headers=headers,
                    timeout=30
                )
            elif method == 'PUT':
                response = requests.put(
                    url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
            elif method == 'PATCH':
                response = requests.patch(
                    url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
            elif method == 'DELETE':
                response = requests.delete(
                    url,
                    headers=headers,
                    timeout=30
                )
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed to {url}: {str(e)}")
            return None

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

    def post(self, request):
        """Handle GraphQL POST requests"""
        try:
            # Parse request body
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                return JsonResponse({
                    'errors': [{'message': 'Content-Type must be application/json'}]
                }, status=400)

            # Extract query for logging
            query = data.get('query', '')

            # Prepare headers for forwarding
            forward_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Forward auth headers if present
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header:
                forward_headers['Authorization'] = auth_header

            # Try v2/graphql first
            v2_url = self.get_v2_url(request)
            v2_response = self.forward_request(v2_url, data, forward_headers, 'POST')

            if v2_response and v2_response.status_code == 200:
                try:
                    v2_data = v2_response.json()
                    # Check if response contains errors
                    if 'errors' not in v2_data or not v2_data['errors']:
                        return JsonResponse(v2_data, status=200)
                    else:
                        # Log v2 GraphQL errors to PostHog
                        error_message = v2_data['errors'][0].get('message', 'Unknown GraphQL error')
                        self.log_error_to_posthog('v2_graphql_error', query, error_message, v2_url)
                except json.JSONDecodeError:
                    self.log_error_to_posthog('v2_json_decode_error', query, 'Invalid JSON response', v2_url)
            else:
                # Log v2 HTTP error to PostHog
                error_message = f"HTTP {v2_response.status_code if v2_response else 'Connection failed'}"
                self.log_error_to_posthog('v2_http_error', query, error_message, v2_url)

            # Fall back to Hasura
            hasura_url = self.get_hasura_url()
            hasura_response = self.forward_request(hasura_url, data, forward_headers, 'POST')

            if hasura_response:
                try:
                    hasura_data = hasura_response.json()
                    return JsonResponse(hasura_data, status=hasura_response.status_code)
                except json.JSONDecodeError:
                    self.log_error_to_posthog('hasura_json_decode_error', query, 'Invalid JSON response', hasura_url)
                    return JsonResponse({
                        'errors': [{'message': 'Invalid response from Hasura service'}]
                    }, status=502)
            else:
                self.log_error_to_posthog('hasura_connection_error', query, 'Connection failed', hasura_url)
                return JsonResponse({
                    'errors': [{'message': 'Both v2 GraphQL and Hasura services are unavailable'}]
                }, status=503)

        except json.JSONDecodeError:
            return JsonResponse({
                'errors': [{'message': 'Invalid JSON in request body'}]
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in GraphQL proxy: {str(e)}")
            self.log_error_to_posthog('proxy_internal_error', '', str(e), '')
            return JsonResponse({
                'errors': [{'message': 'Internal server error'}]
            }, status=500)

    def handle_non_post_request(self, request, method):
        """Handle non-POST requests (GET, HEAD, PUT, PATCH, DELETE)"""
        # Prepare headers for forwarding
        forward_headers = {
            'Accept': 'application/json'
        }
        
        # Forward auth headers if present
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            forward_headers['Authorization'] = auth_header
        
        # For GET requests, use query parameters; for others, try to parse body
        if method == 'GET':
            data = dict(request.GET) if request.GET else None
        else:
            try:
                if request.content_type == 'application/json' and request.body:
                    data = json.loads(request.body)
                    forward_headers['Content-Type'] = 'application/json'
                else:
                    data = None
            except json.JSONDecodeError:
                return JsonResponse({
                    'errors': [{'message': 'Invalid JSON in request body'}]
                }, status=400)
        
        # Try v2/graphql first
        v2_url = self.get_v2_url(request)
        v2_response = self.forward_request(v2_url, data, forward_headers, method)
        
        if v2_response and v2_response.status_code < 400:
            return HttpResponse(
                v2_response.content,
                content_type=v2_response.headers.get('content-type', 'application/json'),
                status=v2_response.status_code
            )
        
        # Fall back to Hasura
        hasura_url = self.get_hasura_url()
        hasura_response = self.forward_request(hasura_url, data, forward_headers, method)
        
        if hasura_response:
            return HttpResponse(
                hasura_response.content,
                content_type=hasura_response.headers.get('content-type', 'application/json'),
                status=hasura_response.status_code
            )
        else:
            return JsonResponse({
                'errors': [{'message': 'GraphQL services are unavailable'}]
            }, status=503)

    def get(self, request):
        """Handle GraphQL GET requests (for GraphiQL introspection)"""
        return self.handle_non_post_request(request, 'GET')

    def head(self, request):
        """Handle GraphQL HEAD requests"""
        return self.handle_non_post_request(request, 'HEAD')

    def put(self, request):
        """Handle GraphQL PUT requests"""
        return self.handle_non_post_request(request, 'PUT')

    def patch(self, request):
        """Handle GraphQL PATCH requests"""
        return self.handle_non_post_request(request, 'PATCH')

    def delete(self, request):
        """Handle GraphQL DELETE requests"""
        return self.handle_non_post_request(request, 'DELETE')
