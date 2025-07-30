from celery import shared_task
import json
from django.core.cache import cache
from typing import Dict, Any, Optional


@shared_task
def refresh_graphql_cache(query: str, variables: Optional[Dict[str, Any]], operation_name: Optional[str], 
                         cache_key: str, ttl: int, user_id: Optional[int] = None):
    """
    Background task to refresh GraphQL query cache
    
    This task executes a GraphQL query and updates the cache with fresh data.
    Used by the CacheExtension when refresh_while_caching is True.
    """
    from superapp.apps.graphql.schema import schema
    from django.contrib.auth import get_user_model
    
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
            except User.DoesNotExist:
                pass
        
        # Execute the GraphQL query
        result = schema.execute_sync(
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
            cache.set(cache_key, cache_data, ttl)
            return f"Cache refreshed for key: {cache_key}"
        else:
            return f"Query execution failed with errors: {result.errors if result else 'No result'}"
            
    except Exception as e:
        return f"Error refreshing cache: {str(e)}"