from __future__ import annotations

import hashlib
import json
import functools
from typing import Any, Callable, Optional, Dict
from django.core.cache import cache
import strawberry
from strawberry.types import Info


def cached_field(
    ttl: int = 60,
    refresh_while_caching: bool = True,
    include_user: bool = False
) -> Callable:
    """
    Decorator for caching GraphQL field results.
    
    Args:
        ttl: Time to live in seconds
        refresh_while_caching: Whether to refresh cache in background while serving cached content
        include_user: Whether to include user ID in cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, info: Info, *args, **kwargs) -> Any:
            # Generate cache key
            cache_key = _generate_field_cache_key(
                field_name=func.__name__,
                args=args,
                kwargs=kwargs,
                user_id=_get_user_id(info) if include_user else None
            )
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                if refresh_while_caching:
                    # Check if there's already a refresh task running
                    refresh_lock_key = f"{cache_key}:refresh_lock"
                    
                    # Try to acquire lock with a short TTL
                    if cache.add(refresh_lock_key, True, timeout=5):
                        # Trigger background refresh
                        from superapp.apps.graphql.tasks import refresh_field_cache
                        refresh_field_cache.delay(
                            self.__class__.__name__,
                            func.__name__,
                            args,
                            kwargs,
                            cache_key,
                            ttl,
                            _get_user_id(info) if include_user else None
                        )
                
                return cached_result
            
            # Execute the field resolver
            result = func(self, info, *args, **kwargs)
            
            # Cache the result
            cache.set(cache_key, result, ttl)
            
            return result
        
        # Mark the field as cached for schema introspection
        wrapper._cached_metadata = {
            "ttl": ttl,
            "refresh_while_caching": refresh_while_caching,
            "include_user": include_user
        }
        
        return wrapper
    return decorator


def _generate_field_cache_key(
    field_name: str,
    args: tuple,
    kwargs: Dict[str, Any],
    user_id: Optional[str] = None
) -> str:
    """Generate a unique cache key for the field"""
    key_data = {
        'field': field_name,
        'args': args,
        'kwargs': kwargs
    }
    
    if user_id:
        key_data['user_id'] = user_id
    
    # Convert to JSON string and hash it
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    prefix = "graphql:field"
    if user_id:
        prefix = f"graphql:user:{user_id}:field"
    
    return f"{prefix}:{field_name}:{key_hash}"


def _get_user_id(info: Info) -> Optional[str]:
    """Extract user ID from GraphQL info context"""
    context = info.context
    
    # Handle both dict and object contexts
    if isinstance(context, dict):
        request = context.get('request')
    else:
        request = getattr(context, 'request', None)
    
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return str(request.user.id)
    
    return None