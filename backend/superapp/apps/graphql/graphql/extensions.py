from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Union

from django.core.cache import cache
from django.http import HttpResponse
from strawberry.extensions import SchemaExtension
from strawberry.types import ExecutionResult, Info


class QueryCache(SchemaExtension):
    """
    GraphQL caching extension that handles both field-level caching (@cached directive)
    and HTTP cache control headers (@cache_control directive)
    """

    def __init__(self):
        super().__init__()
        self.cache_metadata = {}
        self.cache_control_metadata = {}
        self.request = None

    def on_operation(self):
        """Handle operation lifecycle - store request and set headers after execution"""
        # Store request for cache control header handling
        if hasattr(self.execution_context, 'request'):
            self.request = self.execution_context.request
        
        yield  # Allow operation to execute
        
        # Handle cache control headers after operation completion
        self._handle_cache_control_headers()

    def resolve(self, _next, root, info, **kwargs):
        """Handle field-level caching for resolvers with @cached directive"""
        # Collect cache control metadata from root level resolvers
        if info.path.prev is None:  # This is a root field (query/mutation)
            self._collect_cache_control_metadata(info)
        
        # Check if this field should be cached
        cache_config = self.should_cache_field(info)
        
        if cache_config:
            # Try to get cached value
            cached_value = self.get_cached_field_value(info, cache_config, **kwargs)
            if cached_value is not None:
                return cached_value
            
            # Execute resolver and cache result
            result = _next(root, info, **kwargs)
            self.set_cached_field_value(info, result, cache_config, **kwargs)
            return result
        
        # No caching, just execute the resolver
        return _next(root, info, **kwargs)

    def get_cache_key(self, info: Info, **kwargs) -> str:
        """Generate cache key for field-level caching"""
        # Include query path, arguments, and user context
        key_parts = [
            info.field_name,
            info.path.as_list() if hasattr(info.path, 'as_list') else str(info.path),
            json.dumps(kwargs, sort_keys=True, default=str),
        ]

        # Include user ID if authenticated for user-specific caching
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            key_parts.append(f"user:{self.request.user.id}")
        else:
            key_parts.append("anonymous")

        # Create hash of the key parts
        key_string = "|".join(str(part) for part in key_parts)
        return f"graphql:field:{hashlib.md5(key_string.encode()).hexdigest()}"

    def get_cached_field_value(self, info: Info, cache_config: Dict[str, Any], **kwargs) -> Optional[Any]:
        """Get cached field value if available and valid"""
        cache_key = self.get_cache_key(info, **kwargs)
        cached_data = cache.get(cache_key)

        if cached_data is None:
            return None

        # Check if we should refresh while serving cached data
        refresh_while_caching = cache_config.get('refresh_while_caching', True)
        if refresh_while_caching:
            # Check if cache is stale (older than half TTL)
            ttl = cache_config.get('ttl', 60)
            cache_time = cached_data.get('timestamp', 0)
            current_time = time.time()

            if current_time - cache_time > (ttl / 2):
                # Cache is stale, return cached value but don't extend cache
                return cached_data.get('value')

        return cached_data.get('value')

    def set_cached_field_value(self, info: Info, value: Any, cache_config: Dict[str, Any], **kwargs):
        """Cache field value with TTL"""
        cache_key = self.get_cache_key(info, **kwargs)
        ttl = cache_config.get('ttl', 60)

        cached_data = {
            'value': value,
            'timestamp': time.time()
        }

        cache.set(cache_key, cached_data, timeout=ttl)

    def should_cache_field(self, info: Info) -> Optional[Dict[str, Any]]:
        """Check if field has @cached directive"""
        # Get the field definition from the schema
        if info.field_definition and hasattr(info.field_definition, 'resolver'):
            resolver = info.field_definition.resolver
            if hasattr(resolver, '_cached_metadata'):
                return resolver._cached_metadata
        
        # Fallback: check the original resolver
        if hasattr(info, 'parent_type') and hasattr(info.parent_type, '_type_definition'):
            type_def = info.parent_type._type_definition
            for field in type_def.fields:
                if field.python_name == info.field_name:
                    resolver = field.base_resolver
                    if hasattr(resolver, '_cached_metadata'):
                        return resolver._cached_metadata

        return None

    def extract_cache_control_metadata(self, result: ExecutionResult) -> Optional[Dict[str, Any]]:
        """Extract cache control metadata from query/mutation result"""
        # In SchemaExtension, we need to collect metadata during execution
        # Check if we have stored any cache control metadata during operation
        if hasattr(self, '_operation_cache_control_metadata'):
            return self._operation_cache_control_metadata
            
        return None
    
    def _collect_cache_control_metadata(self, info: Info):
        """Collect cache control metadata from root resolvers"""
        # Check if the root resolver (query/mutation) has cache control metadata
        if info.field_definition and hasattr(info.field_definition, 'resolver'):
            resolver = info.field_definition.resolver
            if hasattr(resolver, '_cache_control_metadata'):
                self._operation_cache_control_metadata = resolver._cache_control_metadata

    def build_cache_control_header(self, metadata: Dict[str, Any]) -> str:
        """Build Cache-Control header from metadata"""
        directives = []

        # max-age
        if metadata.get('max_age') is not None:
            directives.append(f"max-age={metadata['max_age']}")

        # stale-while-revalidate
        if metadata.get('stale_while_revalidate') is not None:
            directives.append(f"stale-while-revalidate={metadata['stale_while_revalidate']}")

        # max-stale
        if metadata.get('max_stale') is not None:
            directives.append(f"max-stale={metadata['max_stale']}")

        # Boolean directives
        if metadata.get('public') is True:
            directives.append("public")
        elif metadata.get('private') is True:
            directives.append("private")

        if metadata.get('no_cache') is True:
            directives.append("no-cache")

        if metadata.get('immutable') is True:
            directives.append("immutable")

        return ", ".join(directives)

    def _handle_cache_control_headers(self):
        """Handle cache control headers after operation completion"""
        if not self.request:
            return

        # Check if we have cache control metadata
        if hasattr(self.execution_context, 'result'):
            cache_control_metadata = self.extract_cache_control_metadata(self.execution_context.result)

            if cache_control_metadata:
                cache_control_header = self.build_cache_control_header(cache_control_metadata)

                if cache_control_header:
                    # Set Cache-Control header on the response
                    # First try to access the Django response directly
                    response = getattr(self.execution_context, 'response', None)
                    if response and hasattr(response, '__setitem__'):
                        response['Cache-Control'] = cache_control_header
                    elif hasattr(self.request, '_response') and isinstance(self.request._response, HttpResponse):
                        self.request._response['Cache-Control'] = cache_control_header
                    elif response and hasattr(response, 'headers'):
                        # For strawberry-django integration with newer versions
                        response.headers['Cache-Control'] = cache_control_header
