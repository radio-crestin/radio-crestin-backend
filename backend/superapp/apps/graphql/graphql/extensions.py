from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Union

from django.core.cache import cache
from django.http import HttpResponse
from strawberry.extensions import Extension
from strawberry.types import ExecutionResult, Info


class QueryCache(Extension):
    """
    GraphQL caching extension that handles both field-level caching (@cached directive)
    and HTTP cache control headers (@cache_control directive)
    """
    
    def __init__(self, execution_context=None):
        super().__init__(execution_context)
        self.cache_metadata = {}
        self.cache_control_metadata = {}
        self.request = None
        
    def on_request_start(self):
        """Store request for cache control header handling"""
        if hasattr(self.execution_context, 'request'):
            self.request = self.execution_context.request
    
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
        # Check if field has cached metadata (set by @cached directive)
        if hasattr(info, 'field_nodes') and info.field_nodes:
            field_node = info.field_nodes[0]
            if hasattr(field_node, '_cached_metadata'):
                return field_node._cached_metadata
        
        # Check resolver function for cached metadata
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
        if hasattr(result, '_cache_control_metadata'):
            return result._cache_control_metadata
        
        # Check if any part of the result has cache control metadata
        if result.data and hasattr(result.data, '_cache_control_metadata'):
            return result.data._cache_control_metadata
            
        return None
    
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
    
    def on_operation_end(self):
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
                    if hasattr(self.request, '_response') and isinstance(self.request._response, HttpResponse):
                        self.request._response['Cache-Control'] = cache_control_header
                    elif hasattr(self.execution_context, 'response'):
                        # For strawberry-django integration
                        if hasattr(self.execution_context.response, 'headers'):
                            self.execution_context.response.headers['Cache-Control'] = cache_control_header