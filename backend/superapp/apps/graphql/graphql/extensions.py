from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional
from django.core.cache import cache
from strawberry.extensions import SchemaExtension


class CacheExtension(SchemaExtension):
    """Extension to cache GraphQL query/mutation results based on @cached directive
    
    Note: This is a basic implementation that caches entire query results.
    For production use, consider:
    - Field-level caching for more granular control
    - Cache invalidation strategies
    - User-specific cache keys for authenticated queries
    """
    
    def __init__(self):
        super().__init__()
        self.cached_params: Optional[Dict[str, Any]] = None
        self.cache_key: Optional[str] = None
        self.should_cache = False
    
    def on_parse(self):
        """Called during the parsing phase"""
        yield
        
        # Look for cached directive on the operation
        execution_context = self.execution_context
        
        # Try to find the cached directive
        operation = None
        if hasattr(execution_context, 'graphql_document') and execution_context.graphql_document:
            # Get the first operation definition
            for definition in execution_context.graphql_document.definitions:
                if hasattr(definition, 'operation'):
                    operation = definition
                    break
        
        if operation and hasattr(operation, 'directives') and operation.directives:
            for directive in operation.directives:
                if directive.name.value == 'cached':
                    # Extract the directive arguments
                    self.cached_params = {'ttl': 60, 'refresh_while_caching': True}  # defaults
                    for arg in directive.arguments:
                        arg_name = arg.name.value
                        arg_value = arg.value
                        
                        # Handle different argument value types
                        if hasattr(arg_value, 'value'):
                            value = arg_value.value
                            # Convert string numbers to integers for numeric fields
                            if arg_name == 'ttl' and isinstance(value, str):
                                try:
                                    value = int(value)
                                except ValueError:
                                    pass
                            # Convert string booleans to booleans
                            elif arg_name == 'refresh_while_caching' and isinstance(value, str):
                                value = value.lower() in ('true', '1', 'yes')
                            self.cached_params[arg_name] = value
                        else:
                            self.cached_params[arg_name] = arg_value
                    
                    # Generate cache key
                    self.cache_key = self._generate_cache_key(
                        execution_context.query,
                        execution_context.variables,
                        execution_context.operation_name
                    )
                    self.should_cache = True
                    break
    
    
    def _generate_cache_key(self, query: str, variables: Optional[Dict[str, Any]], operation_name: Optional[str]) -> str:
        """Generate a unique cache key for the query"""
        # Create a dictionary with all the components
        key_data = {
            'query': query,
            'variables': variables or {},
            'operation_name': operation_name or ''
        }
        
        # Convert to JSON string and hash it
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        # Prefix with graphql to avoid collisions
        return f"graphql:query:{key_hash}"


class CacheControlExtension(SchemaExtension):
    """Extension to set HTTP cache control headers based on GraphQL field directives"""
    
    def __init__(self):
        super().__init__()
        self.cache_control_params: Optional[Dict[str, Any]] = None
    
    def on_parsing_start(self):
        """Called when parsing starts"""
        # Reset cache control params for each request
        self.cache_control_params = None
    
    def on_execute(self):
        """Called when the query is about to be executed"""
        result = yield
        
        # Look for cache_control directive on the operation
        execution_context = self.execution_context
        
        
        # Try different ways to access the operation
        operation = None
        if hasattr(execution_context, 'graphql_document') and execution_context.graphql_document:
            # Get the first operation definition
            for definition in execution_context.graphql_document.definitions:
                if hasattr(definition, 'operation'):
                    operation = definition
                    break
        
        if operation:
            
            # Check if the operation has directives
            if hasattr(operation, 'directives') and operation.directives:
                for directive in operation.directives:
                    if directive.name.value == 'cache_control':
                        # Extract the directive arguments
                        self.cache_control_params = {}
                        for arg in directive.arguments:
                            arg_name = arg.name.value
                            arg_value = arg.value
                            
                            # Handle different argument value types
                            if hasattr(arg_value, 'value'):
                                value = arg_value.value
                                # Convert string numbers to integers for numeric fields
                                if arg_name in ['max_age', 'stale_while_revalidate', 'max_stale', 'ttl'] and isinstance(value, str):
                                    try:
                                        value = int(value)
                                    except ValueError:
                                        pass
                                self.cache_control_params[arg_name] = value
                            else:
                                self.cache_control_params[arg_name] = arg_value
                        
                        
                        # Store in context for later use
                        if hasattr(execution_context, 'context'):
                            execution_context.context._cache_control_params = self.cache_control_params
                        break
        
        return result
    
    def on_request_end(self):
        """Called after the request has been processed"""
        # Check if we have cache control params stored in context
        if hasattr(self.execution_context, 'context') and hasattr(self.execution_context.context, '_cache_control_params'):
            cache_control_params = self.execution_context.context._cache_control_params
            
            
            # Build the Cache-Control header value
            cache_control_parts = []
            
            # Handle boolean directives
            if cache_control_params.get('no_cache'):
                cache_control_parts.append('no-cache')
            
            if cache_control_params.get('public'):
                cache_control_parts.append('public')
            elif cache_control_params.get('private'):
                cache_control_parts.append('private')
            
            if cache_control_params.get('immutable'):
                cache_control_parts.append('immutable')
            
            # Handle numeric directives
            max_age = cache_control_params.get('max_age')
            if max_age is not None and not cache_control_params.get('no_cache'):
                cache_control_parts.append(f'max-age={max_age}')
            
            stale_while_revalidate = cache_control_params.get('stale_while_revalidate')
            if stale_while_revalidate is not None:
                cache_control_parts.append(f'stale-while-revalidate={stale_while_revalidate}')
            
            max_stale = cache_control_params.get('max_stale')
            if max_stale is not None:
                cache_control_parts.append(f'max-stale={max_stale}')
            
            # Set the header value in context for the view to use
            if cache_control_parts:
                cache_control_value = ', '.join(cache_control_parts)
                # Set on the context itself
                self.execution_context.context._cache_control_header = cache_control_value
                
                # Set on the request object if it exists (this is what the view will check)
                if hasattr(self.execution_context.context, 'request'):
                    self.execution_context.context.request._cache_control_header = cache_control_value
                
                # Try to set directly on the response if available
                if hasattr(self.execution_context.context, 'response'):
                    response = self.execution_context.context['response']
                    if response:
                        response['Cache-Control'] = cache_control_value
                    
                # Also try the get() method in case context is a dict
                request = getattr(self.execution_context.context, 'request', None) or \
                         (self.execution_context.context.get('request') if hasattr(self.execution_context.context, 'get') else None)
                if request:
                    request._cache_control_header = cache_control_value
