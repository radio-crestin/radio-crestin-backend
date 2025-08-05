"""
REST API Registry for GraphQL queries/mutations

This module provides a class-based mechanism to register GraphQL queries/mutations
as REST API endpoints with custom request/response handling.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class HttpMethod(Enum):
    """Supported HTTP methods for REST API endpoints"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class RestApiEndpoint:
    """Configuration for a REST API endpoint backed by GraphQL"""
    
    # Basic configuration
    path: str  # URL path pattern (e.g., "api/v1/stations" or "api/v1/share-links/<str:anonymous_id>/")
    graphql_query: str  # GraphQL query or mutation
    method: HttpMethod = HttpMethod.GET  # HTTP method
    name: Optional[str] = None  # URL name for Django's reverse()
    
    # Response configuration
    cache_control: Optional[str] = None  # Cache-Control header value
    cors_enabled: bool = True  # Enable CORS headers
    cors_origins: str = "*"  # Allowed CORS origins
    cors_methods: Optional[List[str]] = None  # Allowed CORS methods
    
    # Request/Response transformers
    pre_processor: Optional[Callable] = None  # Pre-process request before GraphQL execution
    post_processor: Optional[Callable] = None  # Post-process GraphQL response
    variable_extractor: Optional[Callable] = None  # Extract GraphQL variables from request
    
    # Additional headers
    extra_headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and set defaults"""
        if self.name is None:
            # Generate name from path
            self.name = self.path.replace("/", "_").replace("<", "").replace(">", "").replace(":", "_")
        
        if self.cors_methods is None:
            # Set default CORS methods based on HTTP method
            if self.method == HttpMethod.GET:
                self.cors_methods = ["GET", "HEAD", "OPTIONS"]
            else:
                self.cors_methods = [self.method.value, "OPTIONS"]


class RestApiRegistry:
    """Registry for REST API endpoints backed by GraphQL"""
    
    _endpoints: Dict[str, RestApiEndpoint] = {}
    
    @classmethod
    def register(cls, endpoint: RestApiEndpoint) -> None:
        """Register a REST API endpoint"""
        if endpoint.path in cls._endpoints:
            raise ValueError(f"Endpoint with path '{endpoint.path}' is already registered")
        cls._endpoints[endpoint.path] = endpoint
    
    @classmethod
    def register_endpoint_class(cls, endpoint_class: type) -> None:
        """
        Register a REST API endpoint from a class
        
        Args:
            endpoint_class: A subclass of RestApiEndpoint with class attributes defined
        """
        # Extract class attributes for endpoint configuration
        config_kwargs = {}
        
        # Required attributes
        if hasattr(endpoint_class, 'path'):
            config_kwargs['path'] = endpoint_class.path
        if hasattr(endpoint_class, 'graphql_query'):
            config_kwargs['graphql_query'] = endpoint_class.graphql_query
            
        # Optional attributes
        if hasattr(endpoint_class, 'method'):
            config_kwargs['method'] = endpoint_class.method
        if hasattr(endpoint_class, 'name'):
            config_kwargs['name'] = endpoint_class.name
        if hasattr(endpoint_class, 'cache_control'):
            config_kwargs['cache_control'] = endpoint_class.cache_control
        if hasattr(endpoint_class, 'cors_enabled'):
            config_kwargs['cors_enabled'] = endpoint_class.cors_enabled
        if hasattr(endpoint_class, 'cors_origins'):
            config_kwargs['cors_origins'] = endpoint_class.cors_origins
        if hasattr(endpoint_class, 'cors_methods'):
            config_kwargs['cors_methods'] = endpoint_class.cors_methods
        if hasattr(endpoint_class, 'extra_headers'):
            config_kwargs['extra_headers'] = endpoint_class.extra_headers
            
        # Method attributes
        if hasattr(endpoint_class, 'pre_processor'):
            config_kwargs['pre_processor'] = endpoint_class.pre_processor
        if hasattr(endpoint_class, 'post_processor'):
            config_kwargs['post_processor'] = endpoint_class.post_processor
        if hasattr(endpoint_class, 'variable_extractor'):
            config_kwargs['variable_extractor'] = endpoint_class.variable_extractor
        
        # Create endpoint instance with extracted configuration
        endpoint = RestApiEndpoint(**config_kwargs)
        
        cls.register(endpoint)
    
    @classmethod
    def get_endpoint(cls, path: str) -> Optional[RestApiEndpoint]:
        """Get endpoint configuration by path"""
        return cls._endpoints.get(path)
    
    @classmethod
    def get_all_endpoints(cls) -> Dict[str, RestApiEndpoint]:
        """Get all registered endpoints"""
        return cls._endpoints.copy()
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered endpoints (useful for testing)"""
        cls._endpoints.clear()


def rest_api(
    path: str,
    graphql_query: str,
    method: HttpMethod = HttpMethod.GET,
    name: Optional[str] = None,
    cache_control: Optional[str] = None,
    cors_enabled: bool = True,
    pre_processor: Optional[Callable] = None,
    post_processor: Optional[Callable] = None,
    variable_extractor: Optional[Callable] = None,
    extra_headers: Optional[Dict[str, str]] = None
):
    """
    Decorator to register a GraphQL query/mutation as a REST API endpoint
    
    Example:
        @rest_api(
            path="api/v1/stations",
            graphql_query=STATIONS_GRAPHQL_QUERY,
            cache_control="public, max-age=14400, immutable",
            pre_processor=add_timestamp_redirect
        )
        def stations_api_config():
            pass
    """
    def decorator(func):
        endpoint = RestApiEndpoint(
            path=path,
            graphql_query=graphql_query,
            method=method,
            name=name,
            cache_control=cache_control,
            cors_enabled=cors_enabled,
            pre_processor=pre_processor,
            post_processor=post_processor,
            variable_extractor=variable_extractor,
            extra_headers=extra_headers or {}
        )
        RestApiRegistry.register(endpoint)
        return func
    
    return decorator