"""
Generic REST API handler for GraphQL-backed endpoints

This module provides a view handler that executes GraphQL queries/mutations
and returns JSON responses for REST API endpoints.
"""

import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional

from django.core.cache import cache
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.utils.http import http_date
from django.views import View
from strawberry.django.context import StrawberryDjangoContext

from superapp.apps.graphql.middleware import carries_credentials
from superapp.apps.graphql.rest_api import CachePolicy, HttpMethod
from superapp.apps.graphql.schema import schema


logger = logging.getLogger(__name__)

# Sent with any response whose body carries GraphQL errors. Without a
# max-age, Django's page cache skips it too (CACHE_MIDDLEWARE_SECONDS = 0).
ERROR_CACHE_POLICY = CachePolicy(header='no-store', ttl=0)


class GraphQLRestApiView(View):
    """
    Generic view for handling REST API requests backed by GraphQL
    
    This view executes GraphQL queries/mutations and returns JSON responses
    with proper headers, caching, and error handling.
    """
    
    endpoint_config = None  # Will be set by factory function
    
    def __init__(self, **kwargs):
        """Initialize the view"""
        super().__init__(**kwargs)
        if not self.endpoint_config:
            raise ValueError("endpoint_config must be set before instantiating view")
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle HTTP method checking"""
        # Check if method is allowed
        if request.method != self.endpoint_config.method.value:
            allowed_methods = [self.endpoint_config.method.value]
            if self.endpoint_config.cors_enabled:
                allowed_methods.append("OPTIONS")
            
            response = JsonResponse(
                {"error": f"Method {request.method} not allowed"},
                status=405
            )
            response['Allow'] = ', '.join(allowed_methods)
            return response
        
        return super().dispatch(request, *args, **kwargs)
    
    def options(self, request, *args, **kwargs):
        """Handle OPTIONS requests for CORS"""
        response = HttpResponse()
        self._add_cors_headers(response)
        response['Allow'] = ', '.join(self.endpoint_config.cors_methods or [self.endpoint_config.method.value])
        return response
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        return self._handle_request(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests"""
        return self._handle_request(request, *args, **kwargs)
    
    def put(self, request, *args, **kwargs):
        """Handle PUT requests"""
        return self._handle_request(request, *args, **kwargs)
    
    def patch(self, request, *args, **kwargs):
        """Handle PATCH requests"""
        return self._handle_request(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """Handle DELETE requests"""
        return self._handle_request(request, *args, **kwargs)
    
    def _handle_request(self, request, *args, **kwargs):
        """
        Main request handler that executes GraphQL and returns response
        """
        try:
            # Check if request is valid (helps catch early disconnects)
            if not request.method or not request.path:
                logger.warning(f"Invalid request received: method={request.method}, path={request.path}")
                return JsonResponse({"error": "Invalid request"}, status=400)

            # Run pre-processor if configured
            if self.endpoint_config.pre_processor:
                pre_result = self.endpoint_config.pre_processor(request, **kwargs)
                if pre_result and 'redirect' in pre_result:
                    # Handle redirect
                    return HttpResponseRedirect(pre_result['redirect'])
                elif pre_result and 'error' in pre_result:
                    # Handle error from pre-processor
                    return JsonResponse(
                        {"error": pre_result['error']},
                        status=pre_result.get('status', 400)
                    )

            # Serve from Redis when the endpoint opts in. These endpoints round
            # their timestamp into fixed windows, so one URL names one snapshot
            # and dozens of concurrent pollers can share a single execution
            # instead of each running the query against Postgres. The entry
            # keeps the time its body was generated, which clients read from
            # Last-Modified to tell whether the answer can still change.
            policy = self.endpoint_config.policy_for(request)
            cache_key = self._response_cache_key(request, policy)
            if cache_key is not None:
                cached = cache.get(cache_key)
                if cached is not None:
                    response = JsonResponse(cached['body'])
                    self._add_headers(
                        response, request, policy, cached['generated_at'])
                    return response

            # Extract GraphQL variables
            variables = {}
            if self.endpoint_config.variable_extractor:
                variables = self.endpoint_config.variable_extractor(request, **kwargs)

            # Execute GraphQL query/mutation
            generated_at = time.time()
            response_data = self._execute_graphql(
                query=self.endpoint_config.graphql_query,
                variables=variables,
                request=request
            )

            # Run post-processor if configured
            if self.endpoint_config.post_processor:
                response_data = self.endpoint_config.post_processor(response_data, request, **kwargs)

            # Only successful results are worth keeping. An error (a resolver
            # failing on a transient database problem) says nothing final
            # about the data, so no cache may keep it: not Redis, not
            # Django's page cache, not the CDN, whatever the request's
            # policy promises for a real answer (`immutable` for settled
            # windows would pin it for 30 days).
            if response_data.get('errors'):
                policy = ERROR_CACHE_POLICY
            elif cache_key is not None:
                cache.set(
                    cache_key,
                    {'body': response_data, 'generated_at': generated_at},
                    policy.ttl,
                )

            # Create JSON response
            response = JsonResponse(response_data)

            # Add headers
            self._add_headers(response, request, policy, generated_at)

            return response

        except Exception as e:
            logger.error(f"Error in REST API handler for {self.endpoint_config.path}: {e}")

            error_response = {
                "errors": [
                    {"message": f"Internal server error: {str(e)}"}
                ]
            }

            response = JsonResponse(error_response, status=500)
            self._add_cors_headers(response)

            return response
    
    def _response_cache_key(self, request, policy) -> Optional[str]:
        """
        Redis key for this request's response, or None if it must not be cached.

        The entry is shared between every caller, so caching is limited to GET
        endpoints that opted in with cache_ttl and whose response depends only
        on the URL. Requests carrying an Authorization header are skipped so a
        privileged response can never land in the shared entry.

        Query parameters are sorted, so the same parameters in a different order
        hit the same entry.
        """
        if policy.ttl <= 0:
            return None
        if request.method != HttpMethod.GET.value:
            return None
        if request.headers.get('Authorization'):
            return None

        params = sorted((key, sorted(values)) for key, values in request.GET.lists())
        key_source = json.dumps([request.path, params, policy.key], separators=(',', ':'))
        digest = hashlib.md5(key_source.encode()).hexdigest()
        # v2: entries hold {'body', 'generated_at'}, not the bare body.
        return f"restapi:v2:{digest}"

    def _execute_graphql(self, query: str, variables: Dict[str, Any], request) -> Dict[str, Any]:
        """
        Execute GraphQL query/mutation using Strawberry schema
        
        Args:
            query: GraphQL query or mutation string
            variables: GraphQL variables
            request: Django request object
            
        Returns:
            Dict with 'data' and optionally 'errors' keys
        """
        # Create a response object for context
        response = HttpResponse()
        
        # Create Strawberry context
        context = StrawberryDjangoContext(request=request, response=response)
        
        # Execute GraphQL
        result = schema.execute_sync(
            query,
            variable_values=variables if variables else None,
            context_value=context
        )
        
        # Prepare response data
        response_data = {"data": result.data}
        
        if result.errors:
            response_data["errors"] = [
                {"message": str(error)} for error in result.errors
            ]
        
        return response_data
    
    def _add_headers(self, response: HttpResponse, request, policy,
                     generated_at: float) -> None:
        """Add all configured headers to response.

        `generated_at` is when the body was computed (epoch seconds), which
        is older than now for a body served from Redis.
        """
        # Add CORS headers
        if self.endpoint_config.cors_enabled:
            self._add_cors_headers(response)

        # The origin's generation time of the body. Caches in front of
        # Django keep it, so a client can tell whether an answer was computed
        # after its data settled. http_date rounds down, which only ever
        # makes an answer look older than it is.
        if not response.has_header('Last-Modified'):
            response['Last-Modified'] = http_date(generated_at)
        
        # Add cache control. A request carrying credentials never gets a
        # shared-cacheable answer, so nothing computed for it can be stored
        # (by Django's page cache or the CDN) and handed to someone else.
        if carries_credentials(request):
            response['Cache-Control'] = 'private, no-store'
        elif policy.header:
            response['Cache-Control'] = policy.header

            # Flag for PublicCacheHeadersMiddleware, which runs last and clears
            # the Vary: Cookie / Accept-Language that Django's session and
            # locale middleware would otherwise append — those make Cloudflare
            # refuse to cache the response at all.
            if 'public' in policy.header.lower():
                response._public_cacheable = True

        # Flag for BoundedUpdateCacheMiddleware (graphql/cache_middleware.py).
        if not policy.page_cacheable:
            response._skip_page_cache = True

        # Add extra headers
        for header, value in self.endpoint_config.extra_headers.items():
            response[header] = value
    
    def _add_cors_headers(self, response: HttpResponse) -> None:
        """Add CORS headers to response"""
        if not self.endpoint_config.cors_enabled:
            return
        
        response['Access-Control-Allow-Origin'] = self.endpoint_config.cors_origins
        response['Access-Control-Allow-Methods'] = ', '.join(
            self.endpoint_config.cors_methods or [self.endpoint_config.method.value]
        )
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Max-Age'] = '86400'  # 24 hours


def create_rest_api_view(endpoint_config):
    """
    Factory function to create a REST API view for an endpoint configuration
    
    Args:
        endpoint_config: RestApiEndpoint configuration object
        
    Returns:
        View function configured for the endpoint
    """
    # Create a new class with the endpoint_config set
    class ConfiguredGraphQLRestApiView(GraphQLRestApiView):
        pass
    
    # Set the endpoint configuration on the class
    ConfiguredGraphQLRestApiView.endpoint_config = endpoint_config
    
    # Return the view function
    return ConfiguredGraphQLRestApiView.as_view()