from __future__ import annotations

from typing import Any, Dict, Optional
from strawberry.extensions import SchemaExtension


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
