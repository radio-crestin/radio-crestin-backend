from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional
from django.core.cache import cache
from strawberry.extensions import SchemaExtension

logger = logging.getLogger(__name__)


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
                    self.cached_params = {'ttl': 60, 'refresh_while_caching': True, 'include_user': False}  # defaults
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
                            elif arg_name in ['refresh_while_caching', 'include_user'] and isinstance(value, str):
                                value = value.lower() in ('true', '1', 'yes')
                            self.cached_params[arg_name] = value
                        else:
                            self.cached_params[arg_name] = arg_value

                    # Get user ID if needed
                    user_id = None
                    if self.cached_params.get('include_user', False):
                        # Try to get user from context
                        if hasattr(execution_context, 'context'):
                            context = execution_context.context
                            # Django request object
                            request = context.get('request') if hasattr(context, 'get') else getattr(context, 'request', None)
                            if request and hasattr(request, 'user') and request.user.is_authenticated:
                                user_id = str(request.user.id)

                    # Generate cache key
                    self.cache_key = self._generate_cache_key(
                        execution_context.query,
                        execution_context.variables,
                        execution_context.operation_name,
                        user_id
                    )
                    self.should_cache = True
                    break

    def on_operation(self):
        """Called when the operation is executed"""
        # Check cache before execution
        if self.should_cache and self.cache_key:
            cached_result = cache.get(self.cache_key)
            if cached_result is not None:
                # Check if we should refresh while serving cached content
                refresh_while_caching = self.cached_params.get('refresh_while_caching', True)
                
                # Set cached result regardless of refresh_while_caching
                from graphql import ExecutionResult
                self.execution_context.result = ExecutionResult(
                    data=cached_result.get('data'),
                    errors=cached_result.get('errors')
                )
                
                if refresh_while_caching:
                    # Check if there's already a refresh task running for this cache key
                    refresh_lock_key = f"{self.cache_key}:refresh_lock"
                    
                    # Try to acquire lock with a short TTL (5 seconds for task to start)
                    # If lock already exists, another refresh is in progress
                    if cache.add(refresh_lock_key, True, timeout=5):
                        # Lock acquired, trigger background refresh
                        from superapp.apps.graphql.tasks import refresh_graphql_cache
                        
                        ttl = self.cached_params.get('ttl', 60)
                        
                        # Get user ID if needed for background refresh
                        user_id = None
                        if self.cached_params.get('include_user', False):
                            context = self.execution_context.context
                            request = context.get('request') if hasattr(context, 'get') else getattr(context, 'request', None)
                            if request and hasattr(request, 'user') and request.user.is_authenticated:
                                user_id = request.user.id
                        
                        logger.debug(f"Triggering background refresh for cache key: {self.cache_key}")
                        refresh_graphql_cache.delay(
                            query=self.execution_context.query,
                            variables=self.execution_context.variables,
                            operation_name=self.execution_context.operation_name,
                            cache_key=self.cache_key,
                            ttl=ttl,
                            user_id=user_id
                        )
                    else:
                        logger.debug(f"Skipping background refresh for cache key {self.cache_key} - refresh already in progress")
                
                yield  # Must yield even when returning cached result
                return

        # Execute the query normally
        yield

        # Cache the result after execution
        if self.should_cache and self.cache_key:
            result = self.execution_context.result
            if result and not (hasattr(result, 'errors') and result.errors):
                # Cache the data
                ttl = self.cached_params.get('ttl', 60)
                cache_data = {
                    'data': result.data,
                    'errors': None
                }
                cache.set(self.cache_key, cache_data, ttl)


    def _generate_cache_key(self, query: str, variables: Optional[Dict[str, Any]], operation_name: Optional[str], user_id: Optional[str] = None) -> str:
        """Generate a unique cache key for the query"""
        # Normalize the query by removing extra whitespace
        normalized_query = ' '.join(query.split())

        # Create a dictionary with all the components
        key_data = {
            'query': normalized_query,
            'variables': variables or {},
            'operation_name': operation_name or ''
        }

        # Add user ID if provided
        if user_id:
            key_data['user_id'] = user_id

        # Convert to JSON string and hash it
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        # Create a more descriptive key prefix
        prefix = "graphql:query"
        if user_id:
            prefix = f"graphql:user:{user_id}:query"

        return f"{prefix}:{key_hash}"


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

        # Skip processing if we don't have a proper execution context (e.g., in background tasks)
        if not hasattr(execution_context, 'graphql_document'):
            return result

        # Try different ways to access the operation
        operation = None
        if execution_context.graphql_document:
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
                            try:
                                context = execution_context.context
                                # Handle both dict and object contexts
                                if isinstance(context, dict):
                                    context['_cache_control_params'] = self.cache_control_params
                                else:
                                    context._cache_control_params = self.cache_control_params
                            except AttributeError:
                                # Skip if context is not accessible (e.g., in background tasks)
                                pass
                        break

        return result

    def on_request_end(self):
        """Called after the request has been processed"""
        # Check if we have cache control params stored in context
        cache_control_params = None
        if hasattr(self.execution_context, 'context'):
            context = self.execution_context.context
            if isinstance(context, dict) and '_cache_control_params' in context:
                cache_control_params = context['_cache_control_params']
            elif hasattr(context, '_cache_control_params'):
                cache_control_params = context._cache_control_params
        
        if cache_control_params:


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
                context = self.execution_context.context
                
                # Handle both dict and object contexts
                if isinstance(context, dict):
                    context['_cache_control_header'] = cache_control_value
                    
                    # Set on request if it exists
                    if 'request' in context and context['request']:
                        request = context['request']
                        if hasattr(request, '__setattr__'):
                            request._cache_control_header = cache_control_value
                    
                    # Set on response if it exists
                    if 'response' in context and context['response']:
                        response = context['response']
                        if hasattr(response, '__setitem__'):
                            response['Cache-Control'] = cache_control_value
                else:
                    # Object context
                    context._cache_control_header = cache_control_value
                    
                    # Set on request if it exists
                    if hasattr(context, 'request') and context.request:
                        context.request._cache_control_header = cache_control_value
                    
                    # Set on response if it exists
                    if hasattr(context, 'response') and context.response:
                        context.response['Cache-Control'] = cache_control_value
