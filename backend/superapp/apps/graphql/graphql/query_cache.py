import hashlib
import json
import time
from typing import Any, Dict, Optional, Union

import strawberry
from django.core.cache import cache
from strawberry.extensions import Extension
from strawberry.types import ExecutionResult


@strawberry.type
class CacheControl:
    """Cache control options for GraphQL queries"""
    max_age: Optional[int] = strawberry.field(default=None, description="Maximum cache age in seconds")
    stale_while_revalidate: Optional[int] = strawberry.field(default=None, description="Stale while revalidate time in seconds")
    no_cache: Optional[bool] = strawberry.field(default=False, description="Disable caching for this query")
    private: Optional[bool] = strawberry.field(default=False, description="Mark cache as private")


class QueryCache(Extension):
    """
    GraphQL Query Cache Extension using Django cache backend
    
    Features:
    - Configurable cache timeout and stale-while-revalidate
    - Cache control headers support
    - Query operation and variables based cache keys
    - Background revalidation for stale content
    """
    
    def __init__(
        self,
        default_timeout: int = 300,  # 5 minutes default
        stale_while_revalidate: int = 60,  # 1 minute stale tolerance
        cache_key_prefix: str = "graphql_query_cache",
        enable_cache_control: bool = True,
        max_query_depth: int = 10,  # Prevent caching of very deep queries
    ):
        self.default_timeout = default_timeout
        self.stale_while_revalidate = stale_while_revalidate
        self.cache_key_prefix = cache_key_prefix
        self.enable_cache_control = enable_cache_control
        self.max_query_depth = max_query_depth
        
    def _generate_cache_key(self, query: str, variables: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> str:
        """Generate a cache key based on query, variables, and optionally user"""
        # Create a deterministic hash of query + variables + user (if needed)
        content = {
            "query": query.strip(),
            "variables": variables or {}
        }
        
        # Add user ID to cache key if cache varies by user
        if user_id and self._should_vary_by_user(query):
            content["user_id"] = user_id
            
        content_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()[:16]
        
        return f"{self.cache_key_prefix}:{content_hash}"
    
    def _should_vary_by_user(self, query: str) -> bool:
        """Check if cache should vary by user based on query directives"""
        # Simple parsing for vary_by_user directive
        if '@cache_control' in query and 'vary_by_user: true' in query.lower():
            return True
        return False
    
    def _get_user_id(self) -> Optional[str]:
        """Get current user ID from execution context if available"""
        try:
            if hasattr(self.execution_context, 'context') and hasattr(self.execution_context.context, 'request'):
                request = self.execution_context.context.request
                if hasattr(request, 'user') and request.user.is_authenticated:
                    return str(request.user.id)
        except Exception:
            pass
        return None
    
    def _get_query_depth(self, query: str) -> int:
        """Calculate approximate query depth to prevent caching very complex queries"""
        # Simple depth calculation based on nested braces
        max_depth = 0
        current_depth = 0
        
        for char in query:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth -= 1
                
        return max_depth
    
    def _should_cache_query(self, query: str, operation_name: Optional[str] = None) -> bool:
        """Determine if a query should be cached"""
        # Don't cache mutations
        if 'mutation' in query.lower():
            return False
            
        # Don't cache subscriptions
        if 'subscription' in query.lower():
            return False
            
        # Don't cache very deep/complex queries
        if self._get_query_depth(query) > self.max_query_depth:
            return False
            
        # Don't cache introspection queries
        if '__schema' in query or '__type' in query:
            return False
            
        return True
    
    def _extract_cache_control(self, result: ExecutionResult) -> Optional[CacheControl]:
        """Extract cache control directives from query result"""
        if not self.enable_cache_control:
            return None
            
        # Try to extract from extensions first
        if result.extensions:
            cache_control_data = result.extensions.get('cacheControl')
            if cache_control_data:
                return CacheControl(
                    max_age=cache_control_data.get('maxAge'),
                    stale_while_revalidate=cache_control_data.get('staleWhileRevalidate'),
                    no_cache=cache_control_data.get('noCache', False),
                    private=cache_control_data.get('private', False)
                )
        
        # Try to extract from GraphQL query directives
        if hasattr(self.execution_context, 'query') and self.execution_context.query:
            query_str = self.execution_context.query
            # Look for @cache_control directive in the query
            if '@cache_control' in query_str:
                # Simple parsing for cache control parameters
                import re
                max_age_match = re.search(r'max_age:\s*(\d+)', query_str)
                swr_match = re.search(r'stale_while_revalidate:\s*(\d+)', query_str)
                no_cache_match = re.search(r'no_cache:\s*(true|false)', query_str)
                private_match = re.search(r'private:\s*(true|false)', query_str)
                
                return CacheControl(
                    max_age=int(max_age_match.group(1)) if max_age_match else None,
                    stale_while_revalidate=int(swr_match.group(1)) if swr_match else None,
                    no_cache=no_cache_match.group(1).lower() == 'true' if no_cache_match else False,
                    private=private_match.group(1).lower() == 'true' if private_match else False
                )
        
        return None
    
    def _get_cache_timeout(self, cache_control: Optional[CacheControl] = None) -> int:
        """Determine cache timeout based on cache control or field-specific settings"""
        if cache_control and cache_control.no_cache:
            return 0
            
        if cache_control and cache_control.max_age is not None:
            return cache_control.max_age
        
        # Check for field-specific cache settings in query
        if hasattr(self.execution_context, 'query') and self.execution_context.query:
            query_str = self.execution_context.query
            # Check for stations query which should have longer cache
            if 'stations' in query_str and 'mutation' not in query_str.lower():
                return 600  # 10 minutes for stations query
            
        return self.default_timeout
    
    def _is_stale(self, cached_at: float, timeout: int, stale_time: int) -> bool:
        """Check if cached content is stale but within stale-while-revalidate window"""
        now = time.time()
        age = now - cached_at
        return timeout < age < (timeout + stale_time)
    
    def on_request_start(self):
        """Hook called at the start of request processing"""
        self._start_time = time.time()
        self._cache_hit = False
        self._cache_key = None
    
    def on_parsing_start(self):
        """Hook called when parsing starts - check cache here"""
        if not hasattr(self.execution_context, 'query') or not self.execution_context.query:
            return
            
        query_string = self.execution_context.query
        variables = getattr(self.execution_context, 'variable_values', None)
        
        # Check if we should cache this query
        if not self._should_cache_query(query_string):
            return
            
        # Generate cache key with user context if needed
        user_id = self._get_user_id()
        self._cache_key = self._generate_cache_key(query_string, variables, user_id)
        
        # Try to get from cache
        cached_data = cache.get(self._cache_key)
        if cached_data:
            cached_result = cached_data.get('result')
            cached_at = cached_data.get('cached_at', 0)
            timeout = cached_data.get('timeout', self.default_timeout)
            
            # Check if cache is fresh
            if not self._is_stale(cached_at, timeout, self.stale_while_revalidate):
                # Cache is fresh, use it
                self._cache_hit = True
                self.execution_context.result = ExecutionResult(
                    data=cached_result.get('data'),
                    errors=cached_result.get('errors'),
                    extensions={
                        **(cached_result.get('extensions') or {}),
                        'cache': {
                            'hit': True,
                            'age': time.time() - cached_at,
                            'ttl': max(0, timeout - (time.time() - cached_at))
                        }
                    }
                )
                return
            elif self._is_stale(cached_at, timeout, self.stale_while_revalidate):
                # Cache is stale but within stale-while-revalidate window
                # Return stale content and mark for background revalidation
                self._cache_hit = True
                self.execution_context.result = ExecutionResult(
                    data=cached_result.get('data'),
                    errors=cached_result.get('errors'),
                    extensions={
                        **(cached_result.get('extensions') or {}),
                        'cache': {
                            'hit': True,
                            'stale': True,
                            'age': time.time() - cached_at,
                            'ttl': 0
                        }
                    }
                )
                # Continue execution to revalidate in background
    
    def on_request_end(self):
        """Hook called at the end of request processing - store in cache"""
        if not self._cache_key or self._cache_hit:
            return
            
        if not hasattr(self.execution_context, 'result') or not self.execution_context.result:
            return
            
        result = self.execution_context.result
        
        # Don't cache if there are errors (unless specifically configured to do so)
        if result.errors:
            return
            
        # Extract cache control from result
        cache_control = self._extract_cache_control(result)
        
        # Get timeout
        timeout = self._get_cache_timeout(cache_control)
        if timeout <= 0:
            return
            
        # Don't cache private responses in shared cache
        if cache_control and cache_control.private:
            return
            
        # Prepare cache data
        cache_data = {
            'result': {
                'data': result.data,
                'errors': [str(error) for error in (result.errors or [])],
                'extensions': result.extensions
            },
            'cached_at': time.time(),
            'timeout': timeout,
            'query_hash': self._cache_key
        }
        
        # Store in cache
        try:
            cache.set(self._cache_key, cache_data, timeout + self.stale_while_revalidate)
        except Exception as e:
            # Log cache error but don't fail the request
            print(f"QueryCache: Failed to store cache: {e}")
            
        # Add cache info to extensions
        if not result.extensions:
            result.extensions = {}
        result.extensions['cache'] = {
            'hit': False,
            'stored': True,
            'ttl': timeout
        }