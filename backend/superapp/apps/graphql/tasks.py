from celery import shared_task
import json
import logging
from django.core.cache import cache
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


@shared_task
def refresh_graphql_cache(query: str, variables: Optional[Dict[str, Any]], operation_name: Optional[str], 
                         cache_key: str, ttl: int, user_id: Optional[int] = None):
    """
    Background task to refresh GraphQL query cache
    
    This task executes a GraphQL query and updates the cache with fresh data.
    Used by the CacheExtension when refresh_while_caching is True.
    """
    from superapp.apps.graphql.schema import background_schema
    from django.contrib.auth import get_user_model
    
    logger.info(f"Starting background cache refresh for key: {cache_key}")
    
    # Extend the lock to cover the actual task execution
    refresh_lock_key = f"{cache_key}:refresh_lock"
    cache.set(refresh_lock_key, True, timeout=30)  # Extend lock for task execution
    
    try:
        # Create context with user if provided
        context = {}
        if user_id:
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                # Create a mock request object with user
                class MockRequest:
                    def __init__(self, user):
                        self.user = user
                        self.META = {}
                
                context['request'] = MockRequest(user)
                logger.debug(f"Added user context for user_id: {user_id}")
            except User.DoesNotExist:
                logger.warning(f"User with id {user_id} not found for cache refresh")
                pass
        
        # Execute the GraphQL query using background schema (no cache extensions)
        result = background_schema.execute_sync(
            query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=context
        )
        
        # Only cache if there are no errors
        if result and not result.errors:
            cache_data = {
                'data': result.data,
                'errors': None
            }
            # Update the cache with fresh data and extend TTL
            cache.set(cache_key, cache_data, ttl)
            logger.info(f"Successfully refreshed cache for key: {cache_key} with TTL: {ttl}s")
            return f"Cache refreshed for key: {cache_key} with TTL: {ttl}s"
        else:
            error_msg = f"Query execution failed with errors: {result.errors if result else 'No result'}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error refreshing cache: {str(e)}"
        logger.exception(error_msg)
        return error_msg
    finally:
        # Always release the lock when done
        cache.delete(refresh_lock_key)
        logger.debug(f"Released refresh lock for key: {cache_key}")


@shared_task
def refresh_field_cache(
    class_name: str,
    field_name: str, 
    args: Tuple,
    kwargs: Dict[str, Any],
    cache_key: str,
    ttl: int,
    user_id: Optional[int] = None
):
    """
    Background task to refresh GraphQL field cache
    
    This task executes a GraphQL field resolver and updates the cache with fresh data.
    Used by the cached_field decorator when refresh_while_caching is True.
    """
    from superapp.apps.graphql.graphql.queries import Query
    from django.contrib.auth import get_user_model
    import strawberry
    
    logger.info(f"Starting background field cache refresh for key: {cache_key}")
    
    # Extend the lock to cover the actual task execution
    refresh_lock_key = f"{cache_key}:refresh_lock"
    cache.set(refresh_lock_key, True, timeout=30)  # Extend lock for task execution
    
    try:
        # Create mock info object
        class MockInfo:
            def __init__(self, context):
                self.context = context
        
        context = {}
        if user_id:
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                # Create a mock request object with user
                class MockRequest:
                    def __init__(self, user):
                        self.user = user
                        self.META = {}
                
                context['request'] = MockRequest(user)
                logger.debug(f"Added user context for user_id: {user_id}")
            except User.DoesNotExist:
                logger.warning(f"User with id {user_id} not found for field cache refresh")
                pass
        
        # Get the query class instance
        if class_name == 'Query':
            instance = Query()
        else:
            logger.error(f"Unknown class name: {class_name}")
            return f"Unknown class name: {class_name}"
        
        # Get the field method
        field_method = getattr(instance, field_name, None)
        if not field_method:
            logger.error(f"Field {field_name} not found on {class_name}")
            return f"Field {field_name} not found on {class_name}"
        
        # Remove the cached decorator wrapper to get the original method
        while hasattr(field_method, '__wrapped__'):
            field_method = field_method.__wrapped__
        
        # Create mock info
        info = MockInfo(context)
        
        # Execute the field resolver
        result = field_method(instance, info, *args, **kwargs)
        
        # Update the cache with fresh data
        cache.set(cache_key, result, ttl)
        logger.info(f"Successfully refreshed field cache for key: {cache_key} with TTL: {ttl}s")
        return f"Field cache refreshed for key: {cache_key} with TTL: {ttl}s"
            
    except Exception as e:
        error_msg = f"Error refreshing field cache: {str(e)}"
        logger.exception(error_msg)
        return error_msg
    finally:
        # Always release the lock when done
        cache.delete(refresh_lock_key)
        logger.debug(f"Released refresh lock for key: {cache_key}")