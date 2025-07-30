from __future__ import annotations

from typing import Any, Dict, Optional
from strawberry.extensions import SchemaExtension


class CacheControlExtension(SchemaExtension):
    """Extension to set HTTP cache control headers based on GraphQL field directives"""
    
    def __init__(self):
        super().__init__()
        self.cache_control_params: Optional[Dict[str, Any]] = None
    
    def on_operation_end(self):
        """Called after the operation has been executed"""
        # Try to find cache control metadata from the executed field
        execution_context = self.execution_context
        
        if hasattr(execution_context, 'result') and execution_context.result:
            # Look for the resolver function that was executed
            if hasattr(execution_context, 'field_nodes') and execution_context.field_nodes:
                for field_node in execution_context.field_nodes:
                    field_name = field_node.name.value
                    
                    # Get the resolver from the schema
                    if execution_context.operation_type == 'query':
                        root_type = execution_context.schema.query
                    elif execution_context.operation_type == 'mutation':
                        root_type = execution_context.schema.mutation
                    else:
                        continue
                    
                    # Find the field in the root type
                    if hasattr(root_type, field_name):
                        field_resolver = getattr(root_type, field_name)
                        
                        # Check if the resolver has cache control metadata
                        if hasattr(field_resolver, '_cache_control_metadata'):
                            self.cache_control_params = field_resolver._cache_control_metadata
                            # Store the cache control params in context for later processing
                            if hasattr(execution_context, 'context'):
                                execution_context.context._cache_control_params = self.cache_control_params
                            break
    
    def get_results(self):
        """Process results and add cache control metadata"""
        result = super().get_results()
        
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
                self.execution_context.context._cache_control_header = cache_control_value
        
        return result
