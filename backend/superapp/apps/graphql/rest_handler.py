"""
Generic REST API handler for GraphQL-backed endpoints

This module provides a view handler that executes GraphQL queries/mutations
and returns JSON responses for REST API endpoints.
"""

import logging
from typing import Dict, Any, Optional

from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.views import View
from strawberry.django.context import StrawberryDjangoContext

from superapp.apps.graphql.schema import schema


logger = logging.getLogger(__name__)


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
            
            # Extract GraphQL variables
            variables = {}
            if self.endpoint_config.variable_extractor:
                variables = self.endpoint_config.variable_extractor(request, **kwargs)
            
            # Execute GraphQL query/mutation
            response_data = self._execute_graphql(
                query=self.endpoint_config.graphql_query,
                variables=variables,
                request=request
            )
            
            # Run post-processor if configured
            if self.endpoint_config.post_processor:
                response_data = self.endpoint_config.post_processor(response_data, request, **kwargs)
            
            # Create JSON response
            response = JsonResponse(response_data)
            
            # Add headers
            self._add_headers(response)
            
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
    
    def _add_headers(self, response: HttpResponse) -> None:
        """Add all configured headers to response"""
        # Add CORS headers
        if self.endpoint_config.cors_enabled:
            self._add_cors_headers(response)
        
        # Add cache control
        if self.endpoint_config.cache_control:
            response['Cache-Control'] = self.endpoint_config.cache_control
        
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